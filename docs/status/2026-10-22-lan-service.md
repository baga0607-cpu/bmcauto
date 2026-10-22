# Local and LAN service — 2026-10-22

## User authorization and launch vocabulary
User approved TCP5000 for same-subnet computers. Their later instruction is binding: 啟動BMCAgent always means loopback-only local mode; only 啟動內網服務 means LAN mode. Never infer LAN mode from the previous running mode. Switch modes by stopping the verified current BMCAgent listener after checking active Tasks, then starting the proper launcher. Do not change the network profile or open broader firewall rules.

## Current setup
Current service is explicitly approved LAN mode at http://<LAN_ADDRESS>:5000 . Launcher bmca-runtime/server-lan.py binds only <LAN_ADDRESS>:5000. Ordinary launcher bmca-runtime/server.py remains 127.0.0.1:5000. Python BMCAgent/.venv/Scripts/python.exe; hidden launch; current launcher PID file bmca-runtime/server.pid. Current LAN mode uses the IP URL even on this computer; 127.0.0.1 is available again when ordinary local mode starts.

Wi-Fi IPv4 <LAN_ADDRESS>, network category DomainAuthenticated. Persistent Windows firewall rule BMCAgent-LAN-5000: inbound allow TCP5000, local address172.17.16.189, remote172.17.16.0/23, interface Wi-Fi, Domain profile, edge traversal blocked. Administrator UAC configuration completed and rule filters independently inspected. No router changes, public exposure, startup automation, login changes or data migration. An IP/subnet/network-category change requires rechecking and narrowly updating the configuration under explicit LAN authorization.

## Verification and limits
No active Tasks before restart. Consistent backup bmca-runtime/backups/lan-service-20261022/before.db. All formal rows unchanged after restart; integrity and foreign keys passed. HTTP requests from this host to the LAN IP return200 for root and API. A second physical computer has not been tested; company Wi-Fi client isolation or network policy could still prevent peers from reaching it.

An attempted all-interface binding was rejected by automatic safety review as broader than authorized; that restart did not execute, source was restored to the specific Wi-Fi address, and the service remained specifically bound. Do not use0.0.0.0 as a workaround.
