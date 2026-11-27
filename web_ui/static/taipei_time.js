'use strict';
const TaipeiTime = (() => {
  const formatter = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
  });
  function format(value) {
    if (!value) return '—';
    let input = value;
    if (typeof input === 'string') {
      input = input.trim().replace(' ', 'T');
      if (/^\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d(?:\.\d+)?)?$/.test(input)) input += '+08:00';
    }
    const instant = new Date(input);
    return Number.isFinite(instant.getTime()) ? formatter.format(instant) : '—';
  }
  function logText(text) {
    // Convert logger headers only. Payloads can include timestamps supplied by the DUT.
    return text.replace(/^(Time: |(?=[^\r\n ]+ - INFO - ))(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d))(?=\r?$| - INFO - )/gm,
      (line, prefix, stamp) => prefix + format(stamp));
  }
  return {format, logText};
})();
