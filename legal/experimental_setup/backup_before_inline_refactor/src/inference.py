import json, re, time
from .labels import canonical_label

def parse_json(raw):
    match=re.search(r"\{.*\}",raw or "",flags=re.S)
    if not match: return {"arguments":[]},"no_json"
    try:
        data=json.loads(match.group(0)); return (data if isinstance(data,dict) else {"arguments":[]}),""
    except json.JSONDecodeError: return {"arguments":[]},"invalid_json"

def align_prediction(text, parsed):
    output=[]; errors=[]
    for item in parsed.get("arguments",[]):
        if not isinstance(item,dict): errors.append("not_object"); continue
        span=item.get("text",""); label=canonical_label(item.get("label")); start=text.find(span) if span else -1
        if start < 0: errors.append("span_not_found"); continue
        if not label: errors.append("unknown_label"); continue
        output.append({"start":start,"end":start+len(span),"text":span,"label":label})
    return output,errors

class LocalGenerator:
    def __init__(self,model_id,quantization=None,max_new_tokens=1024):
        from transformers import AutoTokenizer,AutoModelForCausalLM
        self.tokenizer=AutoTokenizer.from_pretrained(model_id)
        kwargs={"device_map":"auto","torch_dtype":"auto"}
        if quantization=="4bit": kwargs["load_in_4bit"]=True
        self.model=AutoModelForCausalLM.from_pretrained(model_id,**kwargs); self.max_new_tokens=max_new_tokens
    def generate(self,prompt,temperature=0.0,seed=7):
        import torch
        torch.manual_seed(seed); messages=[{"role":"user","content":prompt}]
        inputs=self.tokenizer.apply_chat_template(messages,return_tensors="pt",add_generation_prompt=True) if hasattr(self.tokenizer,"apply_chat_template") else self.tokenizer(prompt,return_tensors="pt").input_ids
        inputs=inputs.to(self.model.device); started=time.perf_counter()
        out=self.model.generate(inputs,max_new_tokens=self.max_new_tokens,do_sample=temperature>0,temperature=max(temperature,.01),pad_token_id=self.tokenizer.eos_token_id)
        return self.tokenizer.decode(out[0][inputs.shape[-1]:],skip_special_tokens=True),time.perf_counter()-started

class VLLMGenerator:
    """Optional inference path for large models such as SaulLM-54B."""
    def __init__(self, model_id, max_new_tokens=1024, **kwargs):
        from vllm import LLM, SamplingParams
        self.llm=LLM(model=model_id, **kwargs); self.params=SamplingParams(temperature=0, max_tokens=max_new_tokens)
    def generate(self, prompt, **kwargs):
        import time
        started=time.perf_counter(); result=self.llm.generate([prompt], self.params)[0]
        return result.outputs[0].text, time.perf_counter()-started
