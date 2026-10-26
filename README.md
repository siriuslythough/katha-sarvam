# Katha — Research, retold

Katha turns uploaded research papers into short, regional-language audio stories for children aged **12–14**. A fictional village elder explains the paper's central idea, methods, results, limitations and implications, with a brief introduction to its authors and institutions.

Built for a hackathon using **Sarvam AI**, with Indian folk-art motifs, patterned borders and a storytelling illustration.

## Current functionality

- **PDF upload and parsing:** Sarvam Document Intelligence digitises the paper. The app checks that all reported pages were returned before proceeding; there is no local PDF-text fallback.
- **Research understanding:** Sarvam-105B analyses extracted text, evidence and page references for an age-appropriate explanation.
- **Four narration languages:** Hindi, English, Punjabi and Telugu. Choose the paper's language and the storytelling language separately.
- **Story writing and review:** Sarvam-105B Conversations writes the story and checks another draft against the analysis and supporting evidence. It is instructed to distinguish analogies from research, and simulations from real deployments.
- **Spoken narration:** Sarvam Bulbul v3 uses the fixed **Ratan** voice for a warm, mature storyteller persona. This is not a clone of a real elder.
- **Audio with synchronized text:** Play, pause, seek, and click a passage to hear it. Highlighting follows passage boundaries calculated from generated WAV files; it is not word-level alignment.
- **Downloads:** Save narration as WAV and the transcript as text.
- **Listener feedback:** Rate the story and explain what you understood in your own words.
- **Two interfaces:** A Streamlit app for cloud deployment and the original localhost website.

Stories currently **aim for 2–3 minutes**. The app adjusts speech pace once when needed and reports recordings that still fall outside the target. Duration is not currently a user-controlled setting.

## Planned features

- **Different narrators:** A choice of voices and storytelling personas.
- **Configurable time limit:** Let listeners choose the desired narration duration.

These are future features, not options available in the current app.

## Sarvam pipeline

```text
Uploaded PDF
    → Sarvam Document Intelligence
    → Sarvam-105B: evidence-based analysis
    → Sarvam-105B Conversations: story writing and factual review
    → Sarvam Bulbul v3: narration in the selected language
    → Audio player + synchronized passages + downloads + feedback
```

All AI processing uses Sarvam APIs. Playback, artwork, timing calculations and downloads run in ordinary application code.

## Run locally

Use Python 3.12 or newer:

```bash
python -m pip install -r requirements.txt
```

Create a local `.env` file and set `SARVAM_API_KEY` to your real Sarvam API key, or provide that environment variable directly. Never commit the key.

Start the Streamlit interface:

```bash
python -m streamlit run streamlit_app.py
```

Or start the original local website:

```bash
python app.py
```

The original website runs at `http://127.0.0.1:8000`. Its local library is stored in the ignored `library/` directory.

## Deploy on Streamlit Community Cloud

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) and connect the GitHub account that owns this repository.
2. Create an app from this repository, choose its default branch, and set the entry point to **`streamlit_app.py`**.
3. In **Advanced settings → Secrets**, add a top-level `SARVAM_API_KEY` TOML entry containing your actual key as a quoted string. Choose Python 3.12 or newer.
4. Deploy. Streamlit supplies the live `.streamlit.app` link for evaluators.

See Streamlit's [deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [secrets documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

Publishing this repository does not itself deploy the app or produce a live website link.

## Evaluator walkthrough

1. Upload a research PDF, choose its source language, and click **Read my paper**.
2. Review the title, authors, institutions and extracted evidence.
3. Choose Hindi, English, Punjabi or Telugu and click **Create my audio story**.
4. Listen, watch the transcript highlight, and click a passage to seek.
5. Download the audio or transcript, rate the story and submit a reflection.

The first run makes real API calls and can take several minutes. Retry an interrupted request to reuse completed work within the same session. The configured Sarvam account needs access to Document Intelligence, chat and TTS, with available credits.

## Data, secrets and prototype limitations

- The API key stays on the server. `.env`, `.streamlit/secrets.toml`, generated files, uploaded-paper caches and temporary files are excluded from Git.
- Uploads are sent to Sarvam for processing. No sample research paper or personal recording is included in this repository.
- The Streamlit app gives each session a separate temporary workspace. Its shelf and feedback are **session-scoped**, not a durable online library. Download outputs before refreshing or leaving; server restarts can remove them. Feedback can also be downloaded as JSON.
- The original localhost app stores its library and feedback on the host device and is intended for single-device use.
- Intended upload size: up to 30 pages / 40 MB, subject to Sarvam service limits. Very long extracted text is rejected rather than silently truncated.
- This prototype delivers audio and synchronized text; video generation is not implemented.
- AI explanations can contain errors. Story review is an additional model pass, not independent scientific verification; check the source paper for important claims.
- Public app usage consumes the owner's Sarvam credits. This hackathon prototype has no user accounts, billing or production abuse controls.

## Project files

| File | Purpose |
| --- | --- |
| `streamlit_app.py` | Streamlit UI, session isolation, player, downloads and feedback |
| `sarvam_pipeline.py` | Document Intelligence, analysis, storytelling, TTS and timing |
| `app.py` | Original local HTTP server |
| `web/` | Original frontend and shared folk illustration |
| `requirements.txt` | Pinned Python dependencies |
| `.streamlit/config.toml` | Theme and upload-size configuration |
| `verify_app.py` | Smoke checks for the original running localhost app and a saved recording |
