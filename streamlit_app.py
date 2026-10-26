"""Streamlit entry point: streamlit run streamlit_app.py."""
import base64
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

from sarvam_pipeline import ROOT, LANGUAGES, STORY_VERSION, analyse_pdf, generate_story, read_json, write_json

st.set_page_config(page_title="Katha · Research, retold", page_icon="🌿", layout="wide")


def player(story, audio):
    """Use WAV-derived passage times for both highlighting and click-to-seek."""
    payload = json.dumps(story["segments"], ensure_ascii=True).replace("<", "\\u003c")
    encoded = base64.b64encode(audio).decode("ascii")
    components.html("""<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;background:#fffdf7;color:#283e34;font:18px/1.8 system-ui,sans-serif}
    audio{width:100%;margin:10px 0}#passages{height:320px;overflow:auto;padding:10px}
    button{display:block;text-align:left;width:100%;border:0;border-left:3px solid transparent;
      background:transparent;color:inherit;font:inherit;padding:12px;cursor:pointer;border-radius:6px}
    button.active{background:#f4e5ca;border-left-color:#b64d2d}button:focus-visible{outline:2px solid #b64d2d}
    .hint{font-size:13px;color:#6e776c}label{font-size:14px}
    </style></head><body><audio id="audio" controls preload="metadata" src="data:audio/wav;base64,"""
    + encoded + """"></audio><label><input id="follow" type="checkbox" checked> Follow the narration</label>
    <p class="hint">Tap a passage to listen from there. Highlighting follows each spoken passage.</p>
    <div id="passages" aria-label="Narration transcript"></div><script>
    const segments=""" + payload + """;
    const audio=document.getElementById('audio'),box=document.getElementById('passages');
    const buttons=segments.map(s=>{const b=document.createElement('button');b.textContent=s.text;
      b.onclick=()=>{audio.currentTime=s.start;audio.play().catch(()=>{});};box.appendChild(b);return b;});
    let active=-1;
    function sync(){const i=segments.findIndex(s=>audio.currentTime>=s.start&&audio.currentTime<s.end);
      if(i===active)return;buttons.forEach((b,j)=>{b.classList.toggle('active',j===i);b.setAttribute('aria-current',j===i?'true':'false');});
      active=i;if(i>=0&&document.getElementById('follow').checked)buttons[i].scrollIntoView({block:'nearest',behavior:'smooth'});}
    audio.addEventListener('timeupdate',sync);audio.addEventListener('seeked',sync);
    </script></body></html>""", height=475, scrolling=False)


def show_error(error):
    status = getattr(error, "status_code", None)
    if status in (401, 403):
        message = "Sarvam denied access. The app owner should check the API key and enabled APIs."
    elif status in (402, 429):
        message = "Sarvam credits or request limits prevented processing. Please try again later."
    elif isinstance(error, ValueError):
        message = str(error)
    else:
        message = "Processing could not finish" + (f" (HTTP {status})" if status else "") + ". Retry to resume saved work."
    st.error(message)


# Community Cloud stores the key in app secrets; local runs can use the ignored .env.
try:
    if st.secrets.get("SARVAM_API_KEY"):
        os.environ["SARVAM_API_KEY"] = str(st.secrets["SARVAM_API_KEY"])
except FileNotFoundError:
    pass

if "workspace" not in st.session_state:
    st.session_state.workspace = tempfile.TemporaryDirectory(prefix="katha-session-")
    st.session_state.papers = {}
    st.session_state.feedback = []
library = Path(st.session_state.workspace.name)

st.markdown("""<style>
.block-container{max-width:1180px;padding-top:2rem}
h1,h2,h3{font-family:Georgia,serif!important}h1{font-size:3.7rem!important}
.folk-border{height:18px;background:repeating-linear-gradient(45deg,#b64d2d 0 2px,transparent 2px 12px),
repeating-linear-gradient(-45deg,#bd9b60 0 2px,transparent 2px 12px);opacity:.65;margin:8px 0 30px}
.eyebrow{color:#b64d2d;letter-spacing:.2em;font-size:12px;font-weight:700}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:18px}
</style><div class="folk-border"></div>""", unsafe_allow_html=True)
heading, illustration = st.columns([3, 2])
with heading:
    st.markdown('<p class="eyebrow">RESEARCH, RETOLD · POWERED BY SARVAM AI</p>', unsafe_allow_html=True)
    st.title("A paper. A story.\nA world of wonder.")
    st.write("Big research ideas, told by a village storyteller — in a language you call home.")
    st.caption("For curious minds aged 12–14 · Hindi · English · Punjabi · Telugu")
with illustration:
    st.image(str(ROOT / "web" / "folk.svg"), width="stretch")

left, right = st.columns([1, 1.5], gap="large")
with left:
    with st.container(border=True):
        st.subheader("01 · Bring a paper")
        upload = st.file_uploader("Upload your research paper", type=["pdf"])
        st.caption("PDF · up to 30 pages · 40 MB. Uploading sends your paper to Sarvam for processing.")
        source_language = st.selectbox("Language of the paper", list(LANGUAGES), index=1, format_func=LANGUAGES.get)
        if st.button("Read my paper", type="primary", disabled=upload is None, width="stretch"):
            with st.status("Reading your paper…", expanded=True) as progress:
                try:
                    paper = analyse_pdf(upload.getvalue(), upload.name, source_language,
                                        lambda text: progress.update(label=text), library_dir=library)
                    st.session_state.papers[paper["id"]] = paper
                    st.session_state.selected_paper = paper["id"]
                    progress.update(label="Paper ready. Choose your storytelling language.", state="complete", expanded=False)
                except Exception as error:
                    progress.update(label="Processing paused", state="error")
                    show_error(error)
    with st.container(border=True):
        st.subheader("02 · Choose your language")
        language = st.selectbox("Listen in", list(LANGUAGES), format_func=LANGUAGES.get)
        st.write("**A village storyteller**")
        st.caption("Ratan · a warm, mature voice · an imagined elder sharing real research")
        st.caption("Stories aim for 2–3 minutes. More narrators and a choice of duration are planned.")
    if st.session_state.papers:
        st.selectbox("Your story shelf", list(st.session_state.papers), key="selected_paper",
                     format_func=lambda value: st.session_state.papers[value]["title"])
    st.caption("Your shelf belongs to this session. Download recordings before closing or refreshing; this demo is not a permanent online library.")

with right:
    paper = st.session_state.papers.get(st.session_state.get("selected_paper"))
    if not paper:
        with st.container(border=True):
            st.subheader("Every discovery begins with a question.")
            st.write("Upload a paper, let Sarvam read it, then settle in for a story.")
            st.caption("Document Intelligence → Sarvam-105B → Bulbul v3")
    else:
        st.subheader(paper["title"])
        authors = paper.get("authors", [])
        st.write(" · ".join(a.get("name", "") if isinstance(a, dict) else str(a) for a in authors))
        st.caption(" · ".join(paper.get("institutions", [])))
        st.caption(f"{paper['pages']} pages processed by Sarvam Document Intelligence")
        with st.expander("Research context, evidence and limitations"):
            st.write(paper.get("core_idea", ""))
            for finding in paper.get("findings", []):
                st.write(finding.get("claim", ""))
                st.caption(f"Pages {finding.get('pages', [])}: {finding.get('evidence', '')}")
            st.write("**Limitations**")
            for limitation in paper.get("limitations", []):
                st.write("• " + str(limitation))
            st.caption(paper.get("coverage_notes", ""))
        output = library / paper["id"] / language
        story_path = output / "story.json"
        story = read_json(story_path) if story_path.exists() else None
        if story and story.get("version") != STORY_VERSION:
            story = None
        if not story and st.button("Create my audio story", type="primary", width="stretch"):
            with st.status("Preparing your story…", expanded=True) as progress:
                try:
                    story = generate_story(paper["id"], language, lambda text: progress.update(label=text), library_dir=library)
                    progress.update(label="Your story is ready", state="complete", expanded=False)
                except Exception as error:
                    progress.update(label="Narration paused", state="error")
                    show_error(error)
        if story:
            st.subheader(story["title"])
            st.caption(f"{LANGUAGES[language]} · {round(story['duration'])} seconds · Sarvam Bulbul v3")
            if story.get("duration_note"):
                st.info(story["duration_note"])
            audio = (output / "narration.wav").read_bytes()
            player(story, audio)
            audio_col, text_col = st.columns(2)
            audio_col.download_button("Download audio", audio, f"katha-{language}.wav", "audio/wav", width="stretch")
            text_col.download_button("Download transcript", (output / "transcript.txt").read_bytes(), f"katha-{language}.txt", "text/plain", width="stretch")
            with st.form(f"feedback-{paper['id']}-{language}"):
                st.subheader("What stayed with you?")
                st.write(story.get("reflection_question", "Explain the idea in your own words."))
                rating = st.radio("Rate this audio story", [1, 2, 3, 4, 5], horizontal=True, index=None)
                understood = st.text_area("What did you understand? Tell us in your own words.", max_chars=3000)
                submitted = st.form_submit_button("Share my reflection")
            if submitted:
                if rating is None or len(understood.strip()) < 3:
                    st.warning("Choose a rating and write a short reflection.")
                else:
                    feedback = {"paper_id": paper["id"], "language": language, "rating": rating,
                                "understood": understood.strip(), "created_at": datetime.now(timezone.utc).isoformat()}
                    st.session_state.feedback.append(feedback)
                    write_json(library / "feedback.json", st.session_state.feedback)
                    st.success("Thank you! Your reflection has been saved for this session.")
            if st.session_state.feedback:
                st.download_button("Save my feedback", json.dumps(st.session_state.feedback, ensure_ascii=False, indent=2), "katha-feedback.json", "application/json")

st.markdown('<div class="folk-border"></div>', unsafe_allow_html=True)
st.caption("Katha · A Sarvam AI hackathon prototype. AI explanations can make mistakes; review the paper and evidence for important claims.")
