# SFX Studio

Local web app: prompt likho → Hugging Face (Stable Audio 3 Space) pe sound generate hoti hai → tumhare computer ke `sounds/` folder mein save ho jati hai.

## Setup

1. huggingface.co pe login karo, `stabilityai/stable-audio-3-small-sfx` model page pe jaa ke license **Agree** karo.
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

## Vercel pe deploy

1. Repo ko Vercel mein import karo. `app.py` khud detect ho jata hai.
2. Vercel dashboard > **Storage** > **Create** > **Blob**, access **Public** rakho, aur store ko is project se connect karo. Sounds wahan save hongi, kyunki Vercel ki disk read-only hai.
3. Project > Settings > **Environment Variables** mein `HF_TOKEN` daalo (zarurat ho to `SPACE_ID`, `API_NAME`, `MODEL_CHOICE` bhi).
4. Redeploy karo.

Blob store connect na ho to app start par hi clear error degi. Local pe Blob token na ho to sounds pehle ki tarah `sounds/` folder mein jati hain.

Note: deployed app pe login nahi hai. Jis ke paas URL hai woh sounds bana aur delete kar sakta hai, aur tumhara HF GPU quota use hoga.
