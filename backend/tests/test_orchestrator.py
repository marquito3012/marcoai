import pytest
import re
import json

# Test simpler parsing logic used in orchestrator
def extract_actions(text):
    json_pattern = r"```(?:json)?\s*([\{\[].*?[\}\]])\s*```"
    matches = re.finditer(json_pattern, text, re.DOTALL | re.IGNORECASE)
    actions = []
    for m in matches:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict):
                actions.append(data)
            elif isinstance(data, list):
                actions.extend(data)
        except:
            continue
    return actions

def infer_action(entry, response_text):
    action = entry.get("action")
    if not action and "name" in entry:
        if "marcar" in response_text.lower() or "hecho" in response_text.lower():
            return "habit_toggle"
        elif "borrar" in response_text.lower() or "eliminar" in response_text.lower():
            return "habit_delete"
        else:
            return "habit_add"
    return action

def test_extract_json_blocks():
    text = """
    Claro, lo haré.
    ```json
    {"action": "habit_toggle", "name": "Correr"}
    ```
    """
    actions = extract_actions(text)
    assert len(actions) == 1
    assert actions[0]["name"] == "Correr"

def test_action_inference_toggle():
    entry = {"name": "Correr"}
    response_text = "He marcado el hábito como hecho."
    action = infer_action(entry, response_text)
    assert action == "habit_toggle"

def test_action_inference_delete():
    entry = {"name": "Correr"}
    response_text = "Voy a eliminar ese hábito de tu lista."
    action = infer_action(entry, response_text)
    assert action == "habit_delete"

def test_multi_block_parsing():
    text = """
    ```json
    {"action": "habit_add", "name": "Bici"}
    ```
    Y este otro:
    ```json
    {"name": "Nadar"}
    ```
    """
    actions = extract_actions(text)
    assert len(actions) == 2
    assert actions[1]["name"] == "Nadar"
    
    # Pruebas de inferencia en el loop
    inf1 = infer_action(actions[0], text)
    inf2 = infer_action(actions[1], text) # Sin palabras clave -> habit_add
    assert inf1 == "habit_add"
    assert inf2 == "habit_add"
