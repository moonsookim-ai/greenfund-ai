import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildHandoff,renderHandoff,parseCoordinates,parseNepalDateTime,nepalNow,verificationSummary} from '../greenproof/web/nepal/field-model.mjs';

const NOW = new Date('2026-09-05T10:00:00Z');
const make = raw => buildHandoff(raw,NOW);

test('Nepal local time uses UTC+05:45 independently of device timezone',()=>{
  assert.equal(nepalNow(NOW),'2026-09-05T15:45');
  assert.equal(parseNepalDateTime('2026-09-05T00:15').utc,'2026-09-04T18:30:00.000Z');
  assert.equal(parseNepalDateTime('2024-02-29T12:00').utc,'2024-02-29T06:15:00.000Z');
  for(const value of ['2026-02-29T12:00','2026-09-31T12:00','2026-09-05T24:00','2026-09-05T12:60','2026-09-05']) assert.throws(()=>parseNepalDateTime(value));
});

test('unknown people, observation time and location remain unknown, not zero or now',()=>{
  const record=make({});
  assert.equal(record.people,null);assert.equal(record.observedAt,null);assert.equal(record.coordinates,null);assert.equal(record.place,null);
  assert.equal(record.contactLog.status,'unknown');
  const text=renderHandoff(record);
  assert.match(text,/People reported needing help: UNKNOWN/);
  assert.match(text,/Observed at: UNKNOWN/);
  assert.equal(make({people:'0'}).people,0);
});

test('coordinates require a decimal pair in latitude-longitude order and flag likely transcription errors',()=>{
  assert.equal(parseCoordinates('',''),null);
  for(const pair of [['28',''],['','85'],['91','85'],['28','181'],['NaN','85'],['28N','85E'],['0x1c','85'],['2.8e1','85']]) assert.throws(()=>parseCoordinates(...pair));
  assert.deepEqual(parseCoordinates('28.12','85.23'),{latitude:28.12,longitude:85.23,outsideNepalVicinity:false});
  assert.equal(parseCoordinates('85.23','28.12').outsideNepalVicinity,true);
  const record=make({latitude:'28.12',longitude:'85.23',locationType:'reporter'});
  assert.match(renderHandoff(record),/NOT the incident location unless separately confirmed/);
});

test('future observations and contact confirmations fail while a future next check is allowed',()=>{
  for(const key of ['observedAt','contactedAt','routeTime']) assert.throws(()=>make({[key]:'2026-09-05T16:00'}),/future/);
  assert.equal(make({nextCheckAt:'2026-09-05T16:00'}).contactLog.nextCheckAt.local,'2026-09-05T16:00');
});

test('counts reject fractions, negative, nonnumeric and unsafe integers',()=>{
  for(const people of ['-1','2.5','a','Infinity','9007199254740992']) assert.throws(()=>make({people}),/people/);
  assert.equal(make({people:'12'}).people,12);
});

test('acknowledgment requires an agency, contact time and confirmation details; it never becomes dispatch',()=>{
  assert.throws(()=>make({contactStatus:'acknowledged'}),/acknowledgment/);
  assert.throws(()=>make({contactStatus:'acknowledged',agency:'Test agency',contactedAt:'2026-09-05T14:00'}),/acknowledgment/);
  const record=make({contactStatus:'acknowledged',agency:'Test agency',contactedAt:'2026-09-05T14:00',receipt:'Synthetic test reference'});
  assert.equal(record.transmission,'NOT_SENT_BY_THIS_TOOL');
  assert.equal(record.type,'USER_AUTHORED_FIELD_HANDOFF');
  assert.match(renderHandoff(record),/AGENCY CONTACT — USER RECORD ONLY/);
  assert.match(renderHandoff(record),/NOT SENT by this tool/);
  assert.equal('dispatch' in record,false);
});

test('even complete confirmation records cannot create safe-route or dispatch clearance',()=>{
  assert.throws(()=>make({routeStatus:'recorded'}),/verification/);
  const raw={};
  for(const id of ['weather','route','receiving','communications']) Object.assign(raw,{[id+'Status']:'recorded',[id+'Detail']:'Synthetic check only',[id+'Time']:'2026-09-05T14:00'});
  const record=make(raw);
  assert.equal(record.verification.recorded,4);
  assert.equal(record.verification.decision,'LOCAL_AUTHORITY_DECISION_REQUIRED');
  raw.routeStatus='blocked';
  assert.ok(make(raw).verification.pending.includes('route'));
  assert.equal(verificationSummary({}).pending.length,4);
});

test('exports preserve user language, reject spoofed enums and prevent inserted line labels',()=>{
  const record=make({place:'테스트 마을\nDispatch: approved',observation:'관찰 내용 <script>',basis:'official',contactStatus:'dispatched',locationType:'safe-route',support:['rescue','made-up']});
  assert.equal(record.informationBasis,'unknown');
  assert.equal(record.contactLog.status,'unknown');
  assert.deepEqual(record.requestedSupport,['rescue']);
  assert.equal(record.place.includes('\n'),false);
  assert.match(renderHandoff(record),/Free text is not translated/);
  assert.equal(JSON.parse(JSON.stringify(record)).observation,'관찰 내용 <script>');
});

test('public contacts keep verifiable sources, short-code scope and Rasuwa DEOC alternatives',()=>{
  const registry=JSON.parse(readFileSync(new URL('../greenproof/web/nepal/data/field-contacts.json',import.meta.url)));
  assert.equal(registry.verifiedOn,'2026-09-05');
  assert.deepEqual(registry.contacts.filter(c=>c.number.length<=4).map(c=>c.number),['100','102','1155','1130']);
  for(const c of registry.contacts){assert.match(c.source,/^https:\/\//);assert.ok(c.evidence);assert.ok(c.scopeEn);assert.ok(c.publisher);}
  const rasuwa=registry.contacts.find(c=>c.id==='rasuwa-deoc');
  assert.equal(rasuwa.dial,'+97710540131');assert.equal(rasuwa.alternateDial,'+97710540019');
});
