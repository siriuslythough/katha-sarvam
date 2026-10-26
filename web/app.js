const $ = id => document.getElementById(id);
let selectedFile, paper, story, busy = false, active = -1, shelf = [];
const copy = {
 'hi-IN': ['आपने क्या सीखा?', 'कहानी की आवाज़ कैसी लगी?', 'अपने शब्दों में बताइए कि आपने क्या समझा।', 'अपने विचार लिखिए…', 'मेरे विचार साझा करें', 'धन्यवाद! आपके विचार इस डिवाइस पर सहेज लिए गए हैं।'],
 'en-IN': ['What stayed with you?', 'How was the audio story?', 'What did you understand, in your own words?', 'Tell us what you understood…', 'Share my thoughts', 'Thank you! Your thoughts were saved on this device.'],
 'pa-IN': ['ਤੁਸੀਂ ਕੀ ਸਿੱਖਿਆ?', 'ਕਹਾਣੀ ਦੀ ਆਵਾਜ਼ ਕਿਵੇਂ ਲੱਗੀ?', 'ਆਪਣੇ ਸ਼ਬਦਾਂ ਵਿੱਚ ਦੱਸੋ ਕਿ ਤੁਸੀਂ ਕੀ ਸਮਝਿਆ।', 'ਆਪਣੇ ਵਿਚਾਰ ਲਿਖੋ…', 'ਮੇਰੇ ਵਿਚਾਰ ਸਾਂਝੇ ਕਰੋ', 'ਧੰਨਵਾਦ! ਤੁਹਾਡੇ ਵਿਚਾਰ ਇਸ ਡਿਵਾਈਸ ਉੱਤੇ ਸੁਰੱਖਿਅਤ ਹਨ।'],
 'te-IN': ['మీరు ఏమి నేర్చుకున్నారు?', 'కథలోని స్వరం ఎలా ఉంది?', 'మీకు అర్థమైన విషయాన్ని మీ సొంత మాటల్లో చెప్పండి.', 'మీ ఆలోచనలు రాయండి…', 'నా ఆలోచనలు పంచుకోండి', 'ధన్యవాదాలు! మీ ఆలోచనలు ఈ పరికరంలో భద్రపరచబడ్డాయి.']
};
async function api(url, options) {
 const response = await fetch(url, options);
 const data = await response.json();
 if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
 return data;
}
function error(message) { $('error').textContent = message; $('error').hidden = !message; }
function controls() {
 $('process').disabled = busy || !selectedFile;
 $('language').disabled = busy || !paper;
 $('generate').disabled = busy || !paper || !$('language').value;
 $('pdf').disabled = busy;
 $('paper-language').disabled = busy;
}
async function runJob(url, options, done) {
 busy = true; controls(); error(''); $('progress').hidden = false;
 $('status-text').textContent = 'Connecting to Sarvam…';
 try {
  const {job_id} = await api(url, options);
  while (true) {
   const job = await api('/api/jobs/' + job_id);
   if (job.status === 'error') throw new Error(job.message);
   if (job.status === 'done') { done(job.result); await loadShelf(); break; }
   $('status-text').textContent = job.message;
   await new Promise(resolve => setTimeout(resolve, 2500));
  }
 } catch (e) { error(e.message); }
 finally { busy = false; $('progress').hidden = true; controls(); }
}
function pickFile(file) {
 if (!file) return;
 if (!file.name.toLowerCase().endsWith('.pdf')) { error('Please choose a PDF file.'); return; }
 selectedFile = file; $('file-label').textContent = file.name; error(''); controls();
}
$('pdf').addEventListener('change', e => pickFile(e.target.files[0]));
for (const event of ['dragenter','dragover']) $('dropzone').addEventListener(event, e => {e.preventDefault(); if(!busy) $('dropzone').classList.add('drag');});
for (const event of ['dragleave','drop']) $('dropzone').addEventListener(event, e => {e.preventDefault(); $('dropzone').classList.remove('drag');});
$('dropzone').addEventListener('drop', e => {if(!busy) pickFile(e.dataTransfer.files[0]);});
$('process').addEventListener('click', () => {
 if (!selectedFile || busy) return;
 $('status-title').textContent = 'Reading your research paper';
 runJob('/api/upload', {method:'POST',headers:{'Content-Type':'application/pdf','X-Filename':encodeURIComponent(selectedFile.name),'X-Paper-Language':$('paper-language').value},body:selectedFile}, showPaper);
});
function resetPlayer() {
 $('audio').pause(); $('audio').removeAttribute('src'); $('audio').load(); story = null; active = -1;
 $('transcript').replaceChildren();
 const p = document.createElement('p'); p.className = 'empty'; p.textContent = 'Choose your language to bring this research to life.'; $('transcript').append(p);
 $('download').hidden = true; $('transcript-download').hidden = true;
 $('feedback-fields').disabled = true; $('feedback').reset(); $('feedback-result').textContent = '';
 $('duration').textContent = 'Your story awaits'; $('story-title').textContent = 'Pull up a seat.';
 $('voice-label').textContent = 'The storyteller is getting ready';
}
function showPaper(data) {
 paper = data; resetPlayer();
 $('paper-title').textContent = data.title;
 $('authors').textContent = (data.authors || []).map(a => typeof a === 'string' ? a : a.name).join(' · ');
 $('institutions').textContent = (data.institutions || []).join(' · ');
 $('core-idea').textContent = data.core_idea || '';
 $('page-count').textContent = data.pages + ' pages · Read';
 $('evidence').hidden = false; $('evidence-body').replaceChildren();
 for (const finding of data.findings || []) {
  const p = document.createElement('p');
  p.textContent = finding.claim + (finding.pages ? ' (pages ' + (Array.isArray(finding.pages) ? finding.pages.join(', ') : finding.pages) + ')' : '');
  $('evidence-body').append(p);
 }
 for (const limitation of data.limitations || []) {const p = document.createElement('p'); p.textContent = 'Limitation: ' + limitation; $('evidence-body').append(p);}
 $('language').value = ''; $('listen-hint').textContent = 'Your paper is ready. Choose Hindi, English, Punjabi or Telugu.';
 controls();
}
$('language').addEventListener('change', () => {
 resetPlayer(); controls();
 const cached = (shelf.find(p => p.id === paper?.id)?.recordings || []).find(s => s.language === $('language').value);
 if (cached) showStory(cached);
});
$('generate').addEventListener('click', () => {
 if (busy || !paper || !$('language').value) return;
 $('status-title').textContent = 'Creating your audio story';
 runJob('/api/narrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paper_id:paper.id,language:$('language').value})},showStory);
});
function timeLabel(seconds) {return Math.floor(seconds/60) + ':' + String(Math.floor(seconds%60)).padStart(2,'0');}
function showStory(data) {
 story = data; active = -1; $('audio').src = data.audio_url;
 $('story-title').textContent = data.title; $('story-title').lang = data.language;
 $('duration').textContent = timeLabel(data.duration) + ' min';
 $('voice-label').textContent = 'Ratan · Your village storyteller';
 $('listen-hint').textContent = data.duration_note || 'Press play. Follow the story, one passage at a time.';
 $('download').href = data.audio_url; $('download').download = `katha-${data.language}.wav`; $('download').hidden = false;
 $('transcript-download').href = data.audio_url.replace('narration.wav','transcript.txt'); $('transcript-download').hidden = false;
 $('transcript').replaceChildren(); $('transcript').lang = data.language;
 data.segments.forEach((segment,index) => {
  const button = document.createElement('button'); button.type = 'button'; button.className = 'passage'; button.textContent = segment.text;
  button.addEventListener('click', async () => { $('audio').currentTime = segment.start; try {await $('audio').play();} catch {error('Press the audio play button to start listening.');} sync(); });
  $('transcript').append(button);
 });
 const c = copy[data.language];
 $('feedback-title').textContent = c[0]; $('rating-label').textContent = c[1];
 $('understood-label').textContent = c[2]; $('understood').placeholder = c[3]; $('feedback-submit').textContent = c[4];
 $('reflection-question').textContent = data.reflection_question || c[2];
 $('reflection').lang = data.language; $('feedback-fields').disabled = false;
 $('feedback').reset(); $('feedback-result').textContent = ''; sync();
}
function sync() {
 if (!story) return;
 const t = $('audio').currentTime;
 let index = story.segments.findIndex(s => t >= s.start && t < s.end);
 if (index < 0) index = story.segments.findLastIndex(s => t >= s.start);
 if (index === active) return;
 const children = $('transcript').children;
 if (active >= 0 && children[active]) {children[active].classList.remove('active'); children[active].removeAttribute('aria-current');}
 active = index;
 if (index >= 0 && children[index]) {
  const el = children[index]; el.classList.add('active'); el.setAttribute('aria-current','true');
  if ($('follow').checked) {
   const container = $('transcript'); const offset = el.getBoundingClientRect().top - container.getBoundingClientRect().top;
   if (offset < 0 || offset + el.offsetHeight > container.clientHeight) container.scrollTop += offset - container.clientHeight/3;
  }
 }
}
for(const event of ['timeupdate','seeked','loadedmetadata']) $('audio').addEventListener(event,sync);
$('audio').addEventListener('ended', () => {$('feedback-title').scrollIntoView({behavior:'smooth',block:'center'});});
$('audio').addEventListener('error', () => {if(story) error('Audio could not be loaded. Try selecting the language again.');});
$('feedback').addEventListener('submit', async e => {
 e.preventDefault(); if (!story) return;
 const rating = Number(new FormData(e.target).get('rating'));
 $('feedback-submit').disabled = true;
 try {
  await api('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paper_id:paper.id,language:story.language,rating,understood:$('understood').value})});
  $('feedback-result').textContent = copy[story.language][5];
 } catch(e) {error(e.message);} finally {$('feedback-submit').disabled = false;}
});
async function loadShelf() {
 shelf = await api('/api/library'); $('library').replaceChildren();
 if (!shelf.length) {const p=document.createElement('p');p.className='fine';p.textContent='Your processed papers will appear here.';$('library').append(p);}
 for (const item of shelf) {
  const button=document.createElement('button'); button.textContent=item.title;
  button.addEventListener('click',()=>{if(!busy){showPaper(item);$('paper-card').scrollIntoView({behavior:'smooth',block:'start'});}});
  $('library').append(button);
 }
 if (!paper && shelf.length) showPaper(shelf[0]);
}
loadShelf().catch(e=>error(e.message));
setInterval(()=>{if(!busy) loadShelf().catch(()=>{});},10000);
