import socket, os
from threading import Thread
import torch

import sys
sys.path.append('../../')
from base import *
sys.path.remove('../../')

# -- Configs --
app.config["REDIS_URL"] = "redis://redis:6379/0"
app.agent_endpoint = "http://web:9000/"
app.LLM_name = "taide2_13b_chat_e11_20240108"
app.version_code = "v1.0"
app.ignore_agent = False
# This is the IP that will be stored in Agent, Make sure the IP address here are accessible by Agent
public_ip = None
if public_ip == None: public_ip = socket.gethostbyname(socket.gethostname())
# The port to use, by choosing None, it'll assign an unused port
app.port = None 
if app.port == None:
    with socket.socket() as s:
        app.port = s.bind(('', 0)) or s.getsockname()[1]
path = "/"
app.reg_endpoint = f"http://{public_ip}:{app.port}{path}"
limit = 1024*3
model_loc = "llama2-13b-ccw_tw8-tv_tulu2_xwin_P2.2e0"
tokenizer_loc = "llama2-13b-ccw_tw8-tv_tulu2_xwin_P2.2e0"
api_key = None
usr_token = None
tc_model = None
# -- Config ends --
# -- Model Part --
# Model Setting
# model part
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig, TextIteratorStreamer, set_seed
from transformers import StoppingCriteria, StoppingCriteriaList

class CustomStoppingCriteria(StoppingCriteria):
    def __init__(self):
        pass

    def __call__(self, input_ids, score, **kwargs) -> bool:
        global proc
        return not proc

model = AutoModelForCausalLM.from_pretrained(model_loc, device_map="auto",torch_dtype=torch.float16)
tokenizer = AutoTokenizer.from_pretrained(tokenizer_loc, add_bos_token=False)
set_seed(42)
generation_config = GenerationConfig(
    temperature=0.2,
    repetition_penalty=1.0
)
system_prompt_fmt = "<s>{0}{1}"
system_text = "你是一個來自台灣的AI助理，由國科會開發，你的名字是 TAIDE，樂於以台灣人的立場幫助使用者，會用繁體中文回答問題。"
prompt_fmt = " USER: {0} ASSISTANT:"
answer_fmt = " {0}"

proc = None

def process(data):
    global proc
    try:
        history = [i['msg'] for i in eval(data.get("input").replace("true","True").replace("false","False"))]
        while len("".join(history)) > limit:
            del history[0]
            del history[0]
        # print(f"History:\n{history}")
        if len(history) != 0:
            history_process = []
            for i in range(0, len(history), 2):
                tmp_txt = ""
                if i == 0:
                    tmp_txt = prompt_fmt.format(history[i])
                    tmp_txt = system_prompt_fmt.format(system_text, tmp_txt)
                else:
                    tmp_txt = prompt_fmt.format(history[i])
                if i != (len(history)-1):
                    tmp_txt = tmp_txt+answer_fmt.format(history[i+1])
                history_process.append(tmp_txt)
            prompt = "".join(history_process)
            print(f"Prompt:\n{prompt.encode('utf-8','ignore').decode('utf-8')}")
            input_ids = tokenizer.encode(prompt, return_tensors='pt').to("cuda:0")
            streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
            generation_kwargs = dict(input_ids=input_ids, streamer=streamer, max_new_tokens=2048,generation_config=generation_config, stopping_criteria=StoppingCriteriaList([CustomStoppingCriteria()]))
            thread = Thread(target=model.generate, daemon=True, kwargs=generation_kwargs)
            thread.start()
            proc = thread
            generated_text = ""
            for new_text in streamer:
                # if "</s>" in new_text:
                #     new_text = new_text.replace("</s>","")
                yield new_text
                if not proc: break
                generated_text += new_text
                torch.cuda.empty_cache()
            thread.join()
            del streamer
            # print(f"Generate:\n{generated_text.encode('utf-8','ignore').decode('utf-8')}")
        else:
            yield "Sorry, The input message is too huge!"

    except Exception as e:
        print(e)
    finally:
        torch.cuda.empty_cache()
        app.Ready[0] = True
        print("finished")

def abort():
    global proc
    if proc:
        tmp = proc
        proc = None
        print("aborting...")
        tmp.join()
        print("aborted")
        torch.cuda.empty_cache()
        return "Aborted"
    return "No process to abort"

# model part ends
app.llm_compute = process
app.abort = abort
start()