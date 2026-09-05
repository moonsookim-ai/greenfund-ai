// Field handoff records are user-authored drafts, never dispatch or triage decisions.
const OFFSET_MS = 345 * 60 * 1000;
export const TIME_ZONE = 'Asia/Kathmandu (UTC+05:45)';
export const clean = (value, limit = 800) => String(value ?? '').replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, limit);

export function nepalNow(date = new Date()) {
  return new Date(date.getTime() + OFFSET_MS).toISOString().slice(0, 16);
}

export function parseNepalDateTime(value) {
  if (!value) return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!match) throw new Error('time');
  const [, year, month, day, hour, minute] = match.map(Number);
  if (year < 2000 || month < 1 || month > 12 || day < 1 || hour > 23 || minute > 59) throw new Error('time');
  const local = Date.UTC(year, month - 1, day, hour, minute);
  if (new Date(local).toISOString().slice(0, 16) !== value) throw new Error('time');
  return {local: value, utc: new Date(local - OFFSET_MS).toISOString(), zone: TIME_ZONE};
}

export function parseCoordinates(latitude, longitude) {
  const lat = String(latitude ?? '').trim(), lon = String(longitude ?? '').trim();
  if (!lat && !lon) return null;
  const decimal = /^[-+]?\d+(?:\.\d+)?$/;
  if (!decimal.test(lat) || !decimal.test(lon)) throw new Error('coordinates');
  const a = Number(lat), b = Number(lon);
  if (!Number.isFinite(a) || !Number.isFinite(b) || a < -90 || a > 90 || b < -180 || b > 180) throw new Error('coordinates');
  // A broad Nepal vicinity check only flags likely transcription errors; it is not a boundary map.
  return {latitude: a, longitude: b, outsideNepalVicinity: a < 26 || a > 31 || b < 80 || b > 89};
}

export function verificationSummary(checks) {
  const categories = ['weather', 'route', 'receiving', 'communications'];
  const pending = categories.filter(id => checks[id]?.status !== 'recorded' || !clean(checks[id]?.detail) || !checks[id]?.checkedAt);
  return {recorded: categories.length - pending.length, pending, blocked: categories.filter(id=>checks[id]?.status === 'blocked'), decision: 'LOCAL_AUTHORITY_DECISION_REQUIRED'};
}

export function buildHandoff(raw, now = new Date()) {
  const dateField = value => {
    const result = parseNepalDateTime(value);
    if (result && Date.parse(result.utc) > now.getTime() + 60000) throw new Error('future');
    return result;
  };
  const countText = String(raw.people ?? '').trim();
  if (countText && (!/^\d+$/.test(countText) || !Number.isSafeInteger(Number(countText)))) throw new Error('people');
  const coordinates = parseCoordinates(raw.latitude, raw.longitude);
  const basis = ['on-site', 'relayed', 'unknown'].includes(raw.basis) ? raw.basis : 'unknown';
  const locationType = ['incident', 'reporter', 'unknown'].includes(raw.locationType) ? raw.locationType : 'unknown';
  const contactStatus = ['unknown', 'attempted', 'acknowledged'].includes(raw.contactStatus) ? raw.contactStatus : 'unknown';
  const contactedAt = dateField(raw.contactedAt);
  if (contactStatus === 'acknowledged' && (!clean(raw.agency) || !contactedAt || !clean(raw.receipt))) throw new Error('acknowledgment');
  const checks = Object.fromEntries(['weather', 'route', 'receiving', 'communications'].map(id => {
    const status = raw[id + 'Status'] === 'recorded' ? 'recorded' : raw[id + 'Status'] === 'blocked' ? 'blocked' : 'unknown';
    const detail = clean(raw[id + 'Detail']);
    const checkedAt = dateField(raw[id + 'Time']);
    if (status === 'recorded' && (!detail || !checkedAt)) throw new Error('verification');
    return [id, {status, detail: detail || null, checkedAt}];
  }));
  const requested = ['rescue', 'medical', 'water', 'shelter', 'access'].filter(key => raw.support?.includes(key));
  return {
    schemaVersion: '1.0', type: 'USER_AUTHORED_FIELD_HANDOFF', transmission: 'NOT_SENT_BY_THIS_TOOL',
    localReference: clean(raw.reference, 70) || 'UNASSIGNED', createdAt: now.toISOString(), timeZone: TIME_ZONE,
    district: clean(raw.district, 120) || null, place: clean(raw.place, 240) || null,
    observedAt: dateField(raw.observedAt), informationBasis: basis,
    people: countText === '' ? null : Number(countText), observation: clean(raw.observation) || null,
    requestedSupport: requested, coordinates: coordinates ? {...coordinates, represents: locationType} : null,
    coordinateSourceNote: coordinates ? clean(raw.coordinateSourceNote, 240) || null : null,
    callback: clean(raw.callback, 180) || null,
    contactLog: {status: contactStatus, agency: clean(raw.agency, 180) || null, contactedAt, receipt: clean(raw.receipt, 240) || null, nextCheckAt: parseNepalDateTime(raw.nextCheckAt)},
    checks, verification: verificationSummary(checks)
  };
}

export function renderHandoff(record) {
  const known = v => v === null || v === '' || v === undefined ? 'UNKNOWN' : v;
  const time = v => v ? `${v.local.replace('T', ' ')} Nepal UTC+05:45` : 'UNKNOWN';
  const coord = record.coordinates;
  const support = {rescue: 'Professional rescue assessment', medical: 'Medical assessment / ambulance', water: 'Safe water / hygiene', shelter: 'Shelter', access: 'Access / logistics coordination'};
  const lines = [
    'NEPAL FLOOD — FIELD HANDOFF DRAFT',
    'NOT SENT by this tool. Contact the appropriate agency yourself.',
    'User-provided information; not independently verified. Free text is not translated.',
    `Local reference (not an official incident ID): ${record.localReference}`,
    `Draft prepared: ${nepalNow(new Date(record.createdAt)).replace('T', ' ')} Nepal UTC+05:45`,
    '', 'LOCATION AND OBSERVATION',
    `District: ${known(record.district)}`, `Place / ward / landmark: ${known(record.place)}`,
    `Observed at: ${time(record.observedAt)}`, `Information basis: ${record.informationBasis}`,
    `People reported needing help: ${known(record.people)}`,
    `Observed situation: ${known(record.observation)}`,
    `Support requested: ${record.requestedSupport.map(id => support[id]).join('; ') || 'UNKNOWN'}`,
    `Coordinates (WGS84, latitude then longitude): ${coord ? `${coord.latitude}, ${coord.longitude}` : 'UNKNOWN'}`,
    `Coordinates represent: ${coord?.represents || 'UNKNOWN'}${coord?.represents === 'reporter' ? ' — NOT the incident location unless separately confirmed' : ''}`,
    `Coordinate source: ${known(record.coordinateSourceNote)}`,
    ...(coord?.outsideNepalVicinity ? ['LOCATION WARNING: outside a broad Nepal vicinity box; recheck before use.'] : []),
    `Callback / team contact: ${known(record.callback)}`,
    '', 'AGENCY CONTACT — USER RECORD ONLY',
    `Contact status recorded by user: ${record.contactLog.status}`,
    `Agency: ${known(record.contactLog.agency)}`, `Contacted at: ${time(record.contactLog.contactedAt)}`,
    `Agency reference / acknowledgment note: ${known(record.contactLog.receipt)}`,
    `Next contact check: ${time(record.contactLog.nextCheckAt)}`,
    '', 'PRE-MOVEMENT CONFIRMATIONS — NOT ROUTE CLEARANCE'
  ];
  for (const [key, check] of Object.entries(record.checks)) lines.push(`${key}: ${check.status} | ${known(check.detail)} | checked ${time(check.checkedAt)}`);
  lines.push('Movement and dispatch decisions remain with local authorities and trained responders.',
    'Do not delay an urgent call while completing this draft. Do not enter floodwater or damaged structures to collect information.',
    'Share location and contact details only with responders who need them.');
  return lines.join('\n');
}
