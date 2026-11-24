#!/usr/bin/env python3
"""Independent semantic rubric judging; no answer or grader hidden truth is exposed."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "claude-opus-5-5"


def public_input(task):
    directory = task / "environment"
    for name in ("inputs.json", "data/inputs.json"):
        if (directory / name).is_file():
            return json.loads((directory / name).read_text())
    return {}


def packet(task, items, artifact, memo):
    public = public_input(task)
    files = {p.name: str(p.resolve()) for p in artifact.iterdir() if p.is_file() and p.suffix in (".xlsx", ".json", ".py", ".md")}
    simulation = {}
    if (artifact / "simulation.json").is_file():
        simulation = json.loads((artifact / "simulation.json").read_text())
    model = {}
    if (artifact / "model.json").is_file():
        model = json.loads((artifact / "model.json").read_text())
    return {
        "task_id": task.name,
        "instruction": (task / "instruction.md").read_text(),
        "public_input": public,
        "public_input_path": str((task / "environment").resolve()),
        "items": [{k: i[k] for k in ("id", "requirement", "evidence", "applies_when")} for i in items],
        "candidate_files": files,
        "memo": memo,
        "model_summary": {k: model.get(k) for k in ("forecast", "valuation", "assumptions") if k in model},
        "simulation_excluding_trials": {k: v for k, v in simulation.items() if k != "trials"},
        "tool_instruction": "只读公开输入、题面和候选交付。不得读取 tests、truth、expected、reference、solution 或评分器。不得修改文件。simulation.json 只看元数据及少量路径，不输出全部 trials。",
    }


def call_llm(item, payload, model, base):
    relevant = {k: payload[k] for k in ("task_id", "instruction", "public_input", "memo", "model_summary", "simulation_excluding_trials")}
    prompt = ("你是 DCF 模型评测的原子 rubric judge。只判断一项，返回严格 JSON："
              '{"item_id":"' + item["id"] + '","score":0或1,"rationale":"具体证据与不足"}。'
              "1 仅在候选交付有明确证据完全满足要求时给；缺少交付或证据不足给 0；不得推测。"
              "题面没有要求的材料不能作为失败理由。开放预测看论证一致性，不猜固定答案。\n"
              "原子要求：" + item["requirement"] + "\n适用条件：" + item["applies_when"] +
              "\n证据：" + json.dumps(relevant, ensure_ascii=False)[:55000])
    attempts = []
    for attempt in range(3):
        body = json.dumps({"model": model, "max_tokens": 2500, "stream": True, "thinking": {"type": "disabled"},
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        request = urllib.request.Request(base + "/v1/messages", data=body,
                                         headers={"content-type": "application/json", "accept": "text/event-stream"})
        text, error = "", None
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                for raw in response:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    try:
                        event = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "content_block_delta" and event.get("delta", {}).get("type") == "text_delta":
                        text += event["delta"].get("text", "")
                    elif event.get("type") == "error":
                        error = str(event.get("error"))[:400]
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:400]
        attempts.append({"attempt": attempt + 1, "error": error, "text_chars": len(text)})
        for match in re.finditer(r"\{", text):
            try:
                answer, _ = json.JSONDecoder().raw_decode(text[match.start():])
            except json.JSONDecodeError:
                continue
            if answer.get("item_id") == item["id"] and answer.get("score") in (0, 1):
                return {"status": "pass" if answer["score"] else "fail", "rationale": answer.get("rationale"), "judge_model": model, "attempts": attempts}
        time.sleep(3)
    return {"status": "unscored", "judge_model": model, "attempts": attempts}


def agent_group(items, payload, model, work):
    work.mkdir(parents=True, exist_ok=True)
    request = work / "request.json"
    request.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    prompt = ("你是只读 DCF 评分 Agent。读取 " + str(request) + "，按其中的 items 和 tool_instruction 检查。"
              "可用 Python/openpyxl 查看工作簿公式、值、工作表结构；每个原子项都必须有真实工具证据。"
              "逐项独立给 0 或 1，缺少证据给 0；题面未要求的 PPT、颜色、打印等不得扣分。"
              "不得读取参考答案、tests、expected、truth 或评分器，不得修改任何文件。"
              '最终只返回 {"scores":{"ID":0或1},"evidence":{"ID":"具体文件、sheet、单元格或字段证据"},"rationale":"简短总结"}。')
    env = dict(os.environ, KIMI_MODEL_BASE_URL="http://127.0.0.1:4310", KIMI_MODEL_PROVIDER_TYPE="anthropic",
               KIMI_MODEL_API_KEY="dummy", KIMI_MODEL_MAX_CONTEXT_SIZE="1048576", KIMI_MODEL_MAX_OUTPUT_SIZE="16000",
               KIMI_MODEL_CAPABILITIES="thinking,tool_use", KIMI_MODEL_THINKING_EFFORT="high", KIMI_MODEL_THINKING_KEEP="off",
               KIMI_LOOP_MAX_ATTEMPTS_PER_STEP="3", HTTP_PROXY="", HTTPS_PROXY="", ALL_PROXY="", NO_COLOR="true", TERM="dumb")
    started = time.time()
    try:
        result = subprocess.run(["/opt/homebrew/bin/kimi", "-m", model, "-p", prompt], cwd=work, env=env,
                                capture_output=True, text=True, timeout=1200)
    except subprocess.TimeoutExpired:
        return {"status": "unscored", "error": "timeout"}
    (work / "agent.log").write_text(result.stdout[-100000:] + "\n" + result.stderr[-10000:])
    for match in re.finditer(r"\{", result.stdout):
        try:
            answer, _ = json.JSONDecoder().raw_decode(result.stdout[match.start():])
        except json.JSONDecodeError:
            continue
        scores = answer.get("scores", {})
        if isinstance(scores, dict) and set(scores) == {i["id"] for i in items} and all(v in (0, 1) for v in scores.values()):
            return {"status": "scored", "scores": scores, "evidence": answer.get("evidence"), "rationale": answer.get("rationale"), "seconds": round(time.time() - started, 1), "judge_model": model}
    return {"status": "unscored", "returncode": result.returncode, "output_excerpt": result.stdout[-1000:]}


def judge(task_name, artifact, output, model, base, agent=True):
    task = ROOT / "tasks" / task_name
    items = json.loads((task / "rubric.json").read_text())["items"]
    memo_path = artifact / "memo.md"
    if not memo_path.exists() and artifact.name == "output.xlsx":
        memo_path = artifact.parent / "memo.md"
    memo = memo_path.read_text(errors="replace") if memo_path.exists() else ""
    artifact = artifact if artifact.is_dir() else artifact.parent
    result = {"task": task_name, "judge_model": model, "generated": dt.datetime.now(dt.timezone.utc).isoformat(), "llm": {}, "agent": {}}
    for item in items:
        if item["method"] != "llm":
            continue
        result["llm"][item["id"]] = call_llm(item, packet(task, [item], artifact, memo), model, base)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    agent_items = [i for i in items if i["method"] == "agent"]
    if agent and agent_items:
        result["agent"] = agent_group(agent_items, packet(task, agent_items, artifact, memo), model, output.with_suffix(""))
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base", default="http://127.0.0.1:4311")
    parser.add_argument("--no-agent", action="store_true")
    args = parser.parse_args()
    result = judge(args.task, args.artifact, args.output, args.model, args.base, not args.no_agent)
    print(json.dumps({"task": args.task, "llm": len(result["llm"]), "agent": result["agent"].get("status", "not_requested"), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
