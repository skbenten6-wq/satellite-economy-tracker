# ... (Keep imports and other functions same) ...
from market_memory import update_global_trend # IMPORT THIS

def generate_grand_strategy(full_data_text):
    if not GEMINI_KEY: return False, "AI Key Missing"
    
    models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']
    
    # NEW PROMPT ASKING FOR JSON
    prompt = (
        "Analyze these 25 macro indicators for India:\n"
        f"{full_data_text}\n\n"
        "STEP 1: Determine the overall market trend (BULLISH, BEARISH, or NEUTRAL).\n"
        "STEP 2: Write a strategy report.\n\n"
        "OUTPUT FORMAT (STRICT JSON):\n"
        "{\n"
        '  "trend": "BULLISH",\n'
        '  "report": "🌍 **MACRO REGIME:** ... (The full report here)"\n'
        "}"
    )
    
    for m in models:
        for attempt in range(2):
            try:
                model = genai.GenerativeModel(m)
                # Ask for JSON response
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                # SAVE TO BRAIN
                update_global_trend(data["trend"])
                
                return True, data["report"]
            except Exception as e:
                time.sleep(10)
                continue
                
    return False, "AI Failed"
