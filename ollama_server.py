import hashlib
import inspect
import json
import time
from datetime import datetime, timezone
import re
import aiohttp
from flask import Flask, jsonify, request

#from ollama_registry import OLLAMA_MODELS
import openllms.clients as clients_module
from openllms.models import LLM

app = Flask(__name__)
DERIVED_MODELS = {}
all_client_dict = {
    name: cls for name, cls in inspect.getmembers(clients_module, inspect.isclass) if issubclass(cls, LLM)
}

def get_fake_digest(name):
    h = hashlib.sha256(name.encode()).hexdigest()
    return f"sha256:{h}"

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def resolve_model(model_name):
    clean_name = model_name.split(":")[0]
    if clean_name in DERIVED_MODELS:
        return DERIVED_MODELS[clean_name]["base"], DERIVED_MODELS[clean_name]["system"]
    return clean_name, ""


def base_response(model):
    return {
        "model": model,
        "created_at": now_iso(),
        "done": True,
        "done_reason": "stop",
        "total_duration": 0,
        "load_duration": 0,
        "prompt_eval_count": 0,
        "prompt_eval_duration": 0,
        "eval_count": 0,
        "eval_duration": 0,
    }


@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Ollama is running"

@app.route("/api/version", methods=["GET"])
def version():
    # Nothing would work unless this endpoint was working
    # Entirely possible this, the show, and the chat endpoints are the only *necessary* ones
    return jsonify({"version": "0.5.7"})


@app.route("/api/tags", methods=["GET"])
def tags():

    #clients = [cls(client=session) for cls in all_client_classes]

    models = []
    # Include both base and derived models
    all_names = list(all_client_dict.keys()) + list(DERIVED_MODELS.keys())

    for name in all_names:
        family = all_client_dict.get(name, {}).name
        models.append(
            {
                "name": f"{name}:latest",
                "model": f"{name}:latest",
                "modified_at": now_iso(),
                "size": 6591830464, #TODO: Does this matter?
                "digest": get_fake_digest(name),
                "details": {
                    "format": "gguf",
                    "family": family,
                    "families": [family],
                    "parameter_size": "4.3B",
                    "quantization_level": "Q4_K_M",
                },
            }
        )
    return jsonify({"models": models})

@app.route("/api/generate", methods=["POST"])
async def generate():
    data = request.json
    raw_model = data["model"]
    model, system_prompt = resolve_model(raw_model)
    prompt = data.get("prompt", "")
    print(prompt)

    entry = all_client_dict.get(model)
    if not entry:
        return jsonify({"error": "model not found"}), 404

    async with aiohttp.ClientSession() as session:
        client = entry(client=session)

        start = time.time()

        full_prompt = f"{system_prompt}\n{prompt}" if system_prompt else prompt
        resp = await client.query(full_prompt)
        duration = int((time.time() - start) * 1e9)

    out = base_response(raw_model)
    out.update({
        "response": resp.message,
        "total_duration": duration,
    })
    print(out)
    return jsonify(out)


@app.route("/api/chat", methods=["POST"])
async def chat():
    data = request.json

    raw_model = data["model"]
    model, system_prompt = resolve_model(raw_model)

    messages = data.get("messages", [])
    tools = data.get("tools", []) # TODO: Look into how tools are formatted, this was just quickly put in place to get Homeassistant working

    entry = all_client_dict.get(model)
    if not entry:
        return jsonify({"error": "model not found"}), 404

    convo = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if content:
            convo.append(f"{role.upper()}: {content}")

    prompt = "\n".join(convo)

    tool_block = ""
    if tools:
        # TODO: Probably not useful to hardcode the TOols prompt in here
        tool_block = "\n\nAVAILABLE TOOLS:\n"
        for t in tools:
            fn = t.get("function", {})
            tool_block += (
                f"- name: {fn.get('name')}\n"
                f"  description: {fn.get('description','')}\n"
                f"  parameters: {json.dumps(fn.get('parameters', {}))}\n"
            )

        tool_block += (
            "\nWhen an action is required, respond ONLY with valid JSON in this format:\n"
            "{\n"
            '  "tool": "<tool name>",\n'
            '  "arguments": { <arguments> }\n'
            "}\n"
            "Do NOT include any extra text.\n"
        )

    full_prompt = f"{system_prompt}\n{tool_block}\n{prompt}" if system_prompt else f"{tool_block}\n{prompt}"

    print("FULL PROMPT:\n", full_prompt)

    async with aiohttp.ClientSession() as session:
        client = entry(client=session)
        start = time.time()
        resp = await client.query(full_prompt)
        duration = int((time.time() - start) * 1e9)

    raw_response = resp.message.strip()
    print("MODEL RESPONSE:", raw_response)

    out = base_response(raw_model)

    # TODO: I'm parsing the tool out manually here, not sure if this is the best way to go about it
    # Ideally the model would just return a response already in the right format?
    tool_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
    if tool_match:
        try:
            tool_json = json.loads(tool_match.group())
            tool_name = tool_json.get("tool")
            arguments = tool_json.get("arguments", {})

            if tool_name:
                out.update(
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": arguments,
                                    },
                                }
                            ],
                        },
                        "total_duration": duration,
                    }
                )
                print("RETURNING TOOL CALL:", tool_name, arguments)
                return jsonify(out)
        except Exception as e:
            print("Tool parse error:", e)

    out.update(
        {
            "message": {
                "role": "assistant",
                "content": raw_response,
            },
            "total_duration": duration,
        }
    )
    return jsonify(out)


@app.route("/api/show", methods=["POST"])
def show():
    data = request.json
    raw_model = data.get("model", "")
    model, _ = resolve_model(raw_model)

    entry = all_client_dict.get(model)
    if not entry:
        return jsonify({"error": "model not found"}), 404
    # TODO: Stole a lot of these values from the output of a real model. Should probably look into what they do
    return jsonify(
        {
            "modelfile": f"FROM {model}\nPARAMETER temperature 0.7",
            "parameters": "temperature 0.7\nnum_ctx 4096",
            "template": "{{ .System }}\nUSER: {{ .Prompt }}\nASSISTANT: ",
            "details": {
                "format": "gguf",
                "family": entry.name,
                "families": entry.name,
                "parameter_size": "4.3B",
                "quantization_level": "Q4_K_M",
            },
        }
    )


@app.route("/api/ps", methods=["GET"])
def ps():
    # Return empty if nothing is "running" or mimic current model
    return jsonify({"models": []})


@app.route("/api/create", methods=["POST"])
def create():
    # TODO: I think ideally I would set this up so you can "create" individual instances of each model, e.g. a Coding Shopify model vs a Chat SHopify model
    data = request.json
    base = data.get("from", "").split(":")[0]
    model = data.get("model", "").split(":")[0]
    system = data.get("system", "")

    if base not in all_client_dict:
        return jsonify({"error": "base model not found"}), 404

    DERIVED_MODELS[model] = {"base": base, "system": system}
    return jsonify({"status": "success"})


@app.route("/api/pull", methods=["POST"])
@app.route("/api/push", methods=["POST"])
def pull_push():
    # Just tell the clients we did it
    return jsonify({"status": "success", "completed": True})


@app.route("/api/delete", methods=["DELETE"])
def delete():
    data = request.json
    model = data.get("model", "").split(":")[0]
    DERIVED_MODELS.pop(model, None)
    return jsonify({"status": "success"})


@app.after_request
def add_headers(resp):
    resp.headers["Content-Type"] = "application/json"
    return resp


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=11434, debug=False)
