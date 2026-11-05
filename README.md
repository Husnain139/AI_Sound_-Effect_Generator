# SFX Studio

Local web app: prompt likho → Hugging Face (Stable Audio 3 Space) pe sound generate hoti hai → tumhare computer ke `sounds/` folder mein save ho jati hai.

## Setup

1. huggingface.co pe login karo, `stabilityai/stable-audio-3-medium` model page pe jaa ke license **Agree** karo.
2. huggingface.co/settings/tokens se ek **Read** token banao.
3. Terminal mein:

```bash
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # Mac/Linux: cp .env.example .env
```

4. `.env` mein `HF_TOKEN` daalo.
5. Run:

```bash
python app.py
```

Browser mein kholo: http://127.0.0.1:8000

## Agar generation fail ho

`python inspect_space.py` chalao. Ye Space ke saare endpoints aur parameters print karega.
Phir `.env` mein `API_NAME` (jaise `/generate`) aur `MODEL_CHOICE` (jaise SFX wala model) set kar do.

## Notes

- Space ZeroGPU pe chalti hai. Free account ka daily GPU quota limited hai; khatam ho jaye to "quota" error aayega. PRO account mein zyada quota milta hai.
- Har sound ke sath ek `.json` file save hoti hai (prompt, date, model, license). Copyright claim aaye to yahi proof hai.
- License: Stability AI Community License. $1M se kam annual revenue tak commercial use free hai; details: stability.ai/license

## Render pe deploy

1. render.com pe **New > Blueprint** chuno aur yeh GitHub repo do. `render.yaml` se service khud ban jayegi (free plan).
2. Render poochega to `HF_TOKEN` daalo.
3. Sounds kahan save hon:
   - **Free plan:** Render ki disk har restart pe saaf hoti hai. Is liye vercel.com pe ek **Public** Blob store banao, uska `BLOB_READ_WRITE_TOKEN` copy karke Render ke env vars mein daalo.
   - **Paid plan:** `render.yaml` mein `disk` wala hissa uncomment karo, `BLOB_READ_WRITE_TOKEN` hata do, aur `SOUNDS_DIR=/var/data/sounds` set karo.

Dono mein se kuch set na ho to app chalti rahegi, lekin har restart pe sounds gum ho jayengi (logs mein WARNING aayegi). Free instance 15 minute idle rehne pe so jata hai; pehli request pe jagne mein thoda waqt lagta hai.

`vercel.json` repo mein hai, Render use ignore karta hai.

Note: deployed app pe login nahi hai. Jis ke paas URL hai woh sounds bana aur delete kar sakta hai, aur tumhara HF GPU quota use hoga.