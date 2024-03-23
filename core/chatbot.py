import openai

openai.api_key = "EMPTY"


class ChatBot:

    def __init__(self, api_base, model="Phind-CodeLlama-34B-v2",temperature=0, max_tokens=4096):
        self.history = []
        self.model = model
        self.max_context = 10
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = ("You are an intelligent programming assistant to help user writing python unit tests. "
                              "If you provide code in your response, the code you write should be in format ```python <code> ```")
        openai.api_base = api_base

    def chat(self, prompt, add_to_history):
        prompts = [{"role":"system", "content": self.system_prompt}]
        context = ""
        
        for history in self.history:
            context += f"{history['question']}\n{history['answer']}\n"
            prompts.append({"role": "user", "content": history['question']})
            prompts.append({"role": "assistant", "content": history['answer']})
        
        prompts.append({"role": "user", "content": prompt})
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=prompts,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        res = response.choices[0].message.content
        if len(self.history) > self.max_context:
            self.history.pop()
        if add_to_history:
            self.history.append({"question":prompt,"answer":res})
        return res


    def chat_cache(self, stage1_prompt, stage1_response=None, stage2_prompt=None):
        prompts = [{"role":"system", "content": self.system_prompt}]

        prompts.append({"role": "user", "content": stage1_prompt})
        if stage1_response:
            prompts.append({"role": "assistant", "content": stage1_response})
        if stage2_prompt:
            prompts.append({"role": "user", "content": stage2_prompt})
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=prompts,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        res = response.choices[0].message.content
        # if len(self.history) > self.max_context:
        #     # self.history.pop(0)
        #     # delete items from the end of the list
        #     self.history.pop()
        # if add_to_history:
        #     self.history.append({"question":prompt,"answer":res})
        return res


if __name__ == "__main__":
    chatbot = ChatBot()
    prompt = 'hi'
    chatbot.chat(prompt, True)
    
    # display(chatbot.history)
    for history in chatbot.history:
        print("Question:")
        print(history["question"])
        print("Answer:")
        print(history["answer"])
    print("----")
