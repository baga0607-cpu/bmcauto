"""Run v1 single-file cases on the current BMCAgent reporting and transport APIs."""
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from urllib.parse import urljoin

import requests

from case_log import ReportedCase
from redfish_route import RedfishRoute, _origin


class _Redfish:
    def __init__(self, ctx, route):
        self.ctx = ctx
        self.route = route

    def traversal(self, **options):
        return self.route.traversal(**options)

    def get(self, uri, *, headers=None, auth=None, timeout=15, redirects=None):
        target = urljoin(self.route.host, uri)
        if auth not in (None, "none") or redirects not in (None, "same_origin"):
            raise ValueError("Unsupported Redfish request options")
        if _origin(target) != self.route.origin and auth != "none":
            raise ValueError("Authenticated GET must stay on the declared origin")
        if redirects == "same_origin":
            if auth or headers or timeout != 15:
                raise ValueError("Unsupported request options for same-origin traversal")
            with self.traversal(redirect_statuses=(301, 302, 307, 308), max_redirects=5,
                                allow_target=lambda uri: True, inspect_hop=lambda hop: None) as get:
                hop = get(target)
                return SimpleNamespace(status_code=hop.status, text=hop.text, uri=hop.uri)
        session = self.ctx.session(self.route, auth)
        response = session.get(target, headers=headers, verify=True if auth == "none" else self.route._verify,
                               timeout=timeout, allow_redirects=False)
        archive = headers and headers.get("Accept") == "*/*"
        body = f"[Archive: {len(response.content)} bytes]" if archive else response.text
        self.ctx.report.log.http("GET", target, response.status_code, response.headers, body,
                                 request_headers=headers)
        return response


class _Context:
    def __init__(self, definition, context, report, stack, preset):
        self.definition = definition
        self.context = context
        self.report = report
        self.stack = stack
        self.parameters = dict(context.get("case_settings") or {})
        if preset is not None:
            self.parameters["preset"] = preset
        self.sessions = {}
        self.routes = {}
        self.blocked = ""
        self.record_counts = {}

    def route(self, name):
        if name not in self.routes:
            self.routes[name] = RedfishRoute(self.context, self.definition["command_routes"][name])
        return self.routes[name]

    def route_origin(self, name):
        return self.route(name).host

    def session(self, route, auth):
        key = (route.origin, auth)
        if key not in self.sessions:
            session = self.stack.enter_context(requests.Session())
            session.trust_env = False
            session.auth = None if auth == "none" else route._auth
            self.sessions[key] = session
        return self.sessions[key]

    def skip_step(self, number, judgement, reason):
        for key, item in self.report.items.items():
            if item["step_number"] == number:
                self.report._report(key, judgement, {"reason": reason})

    def block(self, reason):
        self.blocked = reason

    @contextmanager
    def step(self, number):
        method = next(m for m in self.definition["test_method"] if m["step_number"] == number)
        self.report.begin_step(number)
        step = SimpleNamespace(checkpoint=self.report.checkpoint, operation_result=self.report.operation_result,
                               record=lambda value: self.record(number, value))
        try:
            if "route" in method:
                step.redfish = _Redfish(self, self.route(method["route"]))
            yield step
        except Exception as error:
            self.report.log.end_step(failure=str(error) or type(error).__name__)
            raise
        else:
            self.report.log.end_step()

    def record(self, number, value):
        keys = [key for key, item in self.report.items.items()
                if item["step_number"] == number and item["type"] == "Record"]
        position = self.record_counts.get(number, 0)
        self.report._report(keys[position], "COMPLETED", {"actual": value})
        self.record_counts[number] = position + 1


def execute_case(definition, run, context, preset, failure_type, records=()):
    if not isinstance(context, dict):
        raise RuntimeError("Missing execution context")
    methods = []
    for item in definition["test_method"]:
        methods.append(dict(item, type="Command" if "route" in item else "Action"))
        methods.extend(dict(step_number=number, type="Record", step=label)
                       for number, label in records if number == item["step_number"])
    report = ReportedCase(context, dict(definition, test_method=methods), failure_type)
    observations = {}
    error = blocked = ""
    with ExitStack() as stack:
        ctx = _Context(definition, context, report, stack, preset)
        try:
            observations = run(ctx) or {}
            blocked = ctx.blocked
        except (failure_type, ValueError, requests.RequestException) as exc:
            blocked = str(exc)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    return report.finish(observations, blocked=blocked, error=error)
