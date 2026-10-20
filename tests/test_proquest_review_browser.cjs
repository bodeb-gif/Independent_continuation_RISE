// Run with NODE_PATH pointing to a Playwright installation; uses isolated Chrome profiles.
// Synthetic fixtures are generated in a temporary directory, never in the real pilot.
const {chromium}=require('playwright');
const fs=require('node:fs'), os=require('node:os'), path=require('node:path'), crypto=require('node:crypto');
const assert=require('node:assert/strict');
const R=require('../validation/proquest_review/review.js');
const root=path.resolve(__dirname,'..'), temp=fs.mkdtempSync(path.join(os.tmpdir(),'proquest-review-test-'));
const comparison=JSON.stringify({schema:'proquest-pilot-labels-v1',records:[1,2].map(i=>({audit_id:'SYNTHETIC:'+i,topic:'synthetic_only',direction:'rise'}))});
const pack={schema:'proquest-pilot-v1',rubric:'synthetic-test',pack_id:'synthetic-test-only',
 records:[1,2].map(i=>({audit_id:'SYNTHETIC:'+i,date:'2000-01-01',publisher:'Synthetic fixture'})),
 comparison_sha256:crypto.createHash('sha256').update(comparison).digest('hex')};
const html=fs.readFileSync(path.join(root,'validation/proquest_review/review.html'),'utf8')
 .replace('/* REVIEW_CORE */',fs.readFileSync(path.join(root,'validation/proquest_review/review.js'),'utf8'))
 .replace('/* REVIEW_PACK */',JSON.stringify(pack));
fs.writeFileSync(path.join(temp,'review.html'),html);fs.writeFileSync(path.join(temp,'comparison.json'),comparison);
const url='file://'+path.join(temp,'review.html');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
  const context=await browser.newContext({acceptDownloads:true});const page=await context.newPage();
  const errors=[], network=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
  await page.goto(url);assert(await page.locator('#labels').isDisabled());
  for(const k of R.fields){const loc=page.locator('#f_'+k);if(R.enums[k])await loc.selectOption(R.enums[k][0]);else await loc.fill('Synthetic evidence only');}
  page.once('dialog',d=>d.accept());await page.locator('#lock').click();await page.waitForFunction(()=>document.getElementById('first').disabled);
  assert(await page.locator('#f_reviewer').isDisabled());
  await page.locator('#labels').setInputFiles(path.join(temp,'comparison.json'));await page.waitForFunction(()=>!document.getElementById('reveal').disabled);
  await page.locator('#reveal').click();assert.match(await page.locator('#machine').innerText(),/synthetic_only/);
  await page.locator('#c_topic').selectOption('correct');
  await page.locator('#claim').selectOption('SYNTHETIC:2');assert(await page.locator('#labels').isDisabled());
  assert.equal(await page.locator('#machine').innerText(),'Machine labels hidden.');
  await page.locator('#claim').selectOption('SYNTHETIC:1');assert.equal(await page.locator('#c_topic').inputValue(),'correct');
  for(const k of R.finalFields){const loc=page.locator('#c_'+k);if(R.finalEnums[k])await loc.selectOption(R.finalEnums[k][0]);else await loc.fill('Synthetic comparison only');}
  await page.locator('#finish').click();assert(await page.locator('#c_topic').isDisabled());
  const downloadEvent=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadEvent;
  const exportPath=path.join(temp,'responses.json');await download.saveAs(exportPath);
  const exported=JSON.parse(fs.readFileSync(exportPath));R.validate(exported,pack);
  assert(exported.records['SYNTHETIC:1'].first_pass);assert(exported.records['SYNTHETIC:1'].comparison);
  await page.reload();assert(await page.locator('#f_reviewer').isDisabled());
  const other=await browser.newContext();const restored=await other.newPage();await restored.goto(url);
  await restored.locator('#restore').setInputFiles(exportPath);await restored.waitForFunction(()=>document.getElementById('first').disabled);assert(await restored.locator('#f_reviewer').isDisabled());
  await restored.locator('#restore').setInputFiles(exportPath);await restored.waitForFunction(()=>document.getElementById('message').textContent.includes('empty browser workspace'));
  assert.match(await restored.locator('#message').innerText(),/empty browser workspace/);
  const third=await browser.newContext();const invalid=await third.newPage();await invalid.goto(url);
  exported.pack_id='wrong';const wrong=path.join(temp,'wrong.json');fs.writeFileSync(wrong,JSON.stringify(exported));
  await invalid.locator('#restore').setInputFiles(wrong);await invalid.waitForFunction(()=>document.getElementById('message').textContent.includes('Wrong review pack'));assert.match(await invalid.locator('#message').innerText(),/Wrong review pack/);
  await invalid.locator('#f_reviewer').fill('Synthetic');await invalid.locator('#f_mapping_status').selectOption('unavailable');
  await invalid.locator('#f_mapping_reason').fill('Synthetic missing source');await invalid.locator('#f_blinding').selectOption('unknown');
  invalid.once('dialog',d=>d.accept());await invalid.locator('#lock').click();await invalid.waitForFunction(()=>document.getElementById('first').disabled);assert(await invalid.locator('#labels').isDisabled());
  assert.match(await invalid.locator('#locked').innerText(),/Unassessable/);
  // Inspect the real pack in an empty, isolated browser context; do not enter judgments.
  const realContext=await browser.newContext();const real=await realContext.newPage();
  await real.goto('file://'+path.join(root,'data/scored/proquest/source_review_pilot_v1/review.html'));
  assert.equal(await real.locator('#claim option').count(),12);assert(await real.locator('#labels').isDisabled());
  await real.screenshot({path:path.join(temp,'desktop.png'),fullPage:true});
  const mobileContext=await browser.newContext({viewport:{width:390,height:844}});
  const mobile=await mobileContext.newPage();await mobile.goto(real.url());
  assert(await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.equal(await mobile.locator('header').count(),1);
  await mobile.screenshot({path:path.join(temp,'mobile.png')});
  await mobile.locator('#f_mapping_status').scrollIntoViewIfNeeded();
  await mobile.screenshot({path:path.join(temp,'mobile-form.png')});
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
  console.log(JSON.stringify({status:'passed',checks:['first-pass lock','per-record blinding','comparison autosave','export and restore','wrong-pack rejection','unresolved mappings','12 untouched real records','mobile width','no page errors or network'],screenshots:temp},null,2));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
