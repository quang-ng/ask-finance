from langchain_google_genai import ChatGoogleGenerativeAI


def load_chat_model(model_name: str, temperature: float = 0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
