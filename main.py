import os # dùng os để đọc biến môi trường từ file .env
import requests # requests để gửi HTTP request tới Ollama API
import json
from dotenv import load_dotenv #load_dotenv để load các giá trị trong file .env
from datetime import date
from pathlib import Path
from google import genai
#from openai import OpenAI

load_dotenv()

# Lấy các biến từ file .env 2 biến để phòng trường hợp 1 biến không gọi được
STUDENT_MODEL = os.getenv("STUDENT_MODEL", "qwen3:4b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TEACHER_MODEL = os.getenv("TEACHER_MODEL", "gemini-2.5-flash")
FIELD = "Python basic" #Version 1 thì field sẽ cố định nhưng về sau sẽ thế bằng chủ đề cuẩ subject.txt
MEMORY_DIR = Path("memory")
DATASET_DIR = Path("dataset") / "json"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# TEACHER_MODEL = os.getenv("TEACHER_MODEL", "gpt-4.1-mini")

teacher_client = genai.Client(api_key=GEMINI_API_KEY)


def ask_student(prompt):
    """
    Func gửi prompt cho local Student AI thông qua Ollama
    Student sẽ tạo câu hỏi hoặc câu trả lời dựa trên prompt.
    """
    
    response = requests.post(
        OLLAMA_URL, #:ấy Ollama URL
        json={
            "model": STUDENT_MODEL, #model hiệnt tại là qwen3:4b 
            "prompt": prompt, #Nội dung mình muốn prompt
            "stream":False #Đợi model trả lời xong mới nhận kết quả
        },
        timeout = 300
    )
    #Nếu có err sẽ báo lỗi status
    response.raise_for_status()
    
    #Ollama trả về JSON, mình lấy phần "response" là câu trả lời của model
    return response.json()["response"]

def ask_teacher(question):
    """
    Teacher AI dùng Gemini API để trả lời câu hỏi của Student.
    """
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY in .env file.")
    teacher_prompt = f"""
    You are a Teacher AI.
    
    Your job is to teach a beginner student clearly and accurately.
    
    Student question:
    {question}
    
    Rules:
    Answer only the student's question.
    Keep the explaination beginner-friendly.
    Give one simple example.
    Mention one common beginner mistake if useful.
    Do not talk about unrelated topics.
    """
    response = teacher_client.models.generate_content(
        model=TEACHER_MODEL,
        contents=teacher_prompt
    )
    return response.text

def student_generate_dataset(field, student_question, teacher_answer, memory):
    """
    Student dùng kiến thức Teacher vừa dạy để tạo 5 cặp prompt completion dạng JSON.
    """
    
    prompt = f"""
    You are Local Student AI.
    
    You are learning topic: {field}
    
    This is your previous memory:
    {memory}
    
    You ask Teacher this question:
    {student_question}
    
    Teacher has answered:
    {teacher_answer}
    
    Tasks:
    Based on the knowledge that the Teacher just taught you and your previous memory, create exactly 5 sample question-and-answer pairs.
    
    Requirementns:
    Return only plain JSON text.
    Do not add any extra explaination.
    Do not use markdown.
    DO not wrap the output with ''' json.
    The JSON must be array.
    Each item must have exactly 2 keys: "prompt" and "completion".
    "prompt" is the question.
    "completion" is the answer.
    The questions must be suitable for beginners.
    The answer must be short, clear, and focused.
    The content must be based on the knowledge from the Teacher's answer.
    
    Required format:
    [
        {{
            "prompt": "question",
            "completion": "answer"
        }}
    ]
    """
    return ask_student(prompt)

def parse_dataset_json(raw_output):
    """
    Parse output JSON từ Student.
    """
    cleaned_output = raw_output.strip()
    cleaned_output = cleaned_output.replace("```json", "").replace("```", "").strip()
    
    start = cleaned_output.find("[")
    end = cleaned_output.rfind("]")
    
    if start != -1 and end != -1:
        cleaned_output = cleaned_output[start:end + 1]
        
    try:
        dataset_pairs = json.loads(cleaned_output)
    except json.JSONDecodeError:
        print("\nError: Student output is not valid JSON.")
        print("Raw output:")
        print(raw_output)
        return []
    
    valid_pairs = []
    
    for item in dataset_pairs:
        if isinstance(item, dict) and "prompt" in item and "completion" in item:
            valid_pairs.append({
                "prompt": item["prompt"],
                "completion": item["completion"]
            })
    return valid_pairs

# def student_self_study(question, teacher_answer):
#     prompt = f"""
#     You are local Student AI.
    
#     You asked this question:
#     {question}
    
#     The Teacher answered:
#     {teacher_answer}
    
#     Now study the Teacher's answer by yourself.
    
#     Write this structure:
    
#     # My Understanding
#     Explain the idea again in your own words.
    
#     # Simple Example
#     Create one simple example.
    
#     # Key Points
#     List 3 important points.
    
#     # Self Quiz
#     Create 3 quiz questions.
    
#     # My Quiz Answers
#     Answer your own quiz questions.
    
#     # Confusion
#     Write what you are still unsure about. If nothing, write "No major confusion."
    
#     Important:
#     Do not copy the Teacher word for word. Learn it and explain it like a real student. 
#     """
    
#     return ask_student(prompt)

#Những hàm hỗ trợ đặt tên cho file
def safe_name(text):
    return text.strip().lower().replace(" ", "_")

def today_text():
    return date.today().isoformat()

def get_paths(field):
    field_name = safe_name(field)
    today = today_text()
    
    memory_path = MEMORY_DIR / f"{field_name}.md"
    dataset_json_path = DATASET_DIR / f"{today}_{field_name}.json"
    
    return memory_path, dataset_json_path

def save_learning(field, dataset_pairs):
    memory_path, dataset_json_path = get_paths(field)
    
    #Nếu file JSON hôm nay đã tồn tại, đọc dữ liệu cũ
    if dataset_json_path.exists():
        with open(dataset_json_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []
    
    #Thêm dữ liệu mới vào dữ liệu cũ
    existing_data.extend(dataset_pairs)
    
    
    # Lưu dataset JSON của ngày hôm nay
    with open(dataset_json_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    
    # Lưu memory cùng dạng JSON để lần sau Student đọc lại
    with open(memory_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        print("\nSaved file:")
        print(f"- JSON dataset: {dataset_json_path}")
        print(f"- Memory: {memory_path}")
        
def load_memory(field):
    memory_path, dataset_json_path = get_paths(field)
    
    if not memory_path.exists():
        return "No previous memory yet."
    
    with open(memory_path, "r", encoding="utf-8") as f:
        memory = f.read()
    #Cố giới hạn memory để tránh khi prompt quá dài gây timeout    
    return memory[-2000:]
        
def main():
    """
    Flow chính:
    1. Load memory cũ
    2. Student tạo 1 câu hỏi chung để hỏi Teacher
    3. Teacher trả lời
    4. Student tạo 5 cặp prompt/completion từ Teacher answer
    5. Parse JSON
    6. Lưu journal, memory, dataset jsonl
    """
    memory = load_memory(FIELD)

    prompt = f"""
You are the local Student AI.

You are learning this field:
{FIELD}

Here is your previous memory:
{memory}

Create one general beginner-friendly question to ask the Teacher AI about today's topic.

Rules:
1. Ask only one question.
2. The question should help you learn a useful basic concept about this field.
3. Do not answer the question.
4. Return only the question text.
"""

    # Student tạo 1 câu hỏi chung
    student_question = ask_student(prompt).strip()
    print("Student question:", student_question)

    # Teacher trả lời câu hỏi đó
    teacher_answer = ask_teacher(student_question)
    print("\nTeacher answer:", teacher_answer)

    # Student tạo 5 cặp prompt/completion dựa trên Teacher answer
    raw_dataset_output = student_generate_dataset(
        FIELD,
        student_question,
        teacher_answer,
        memory
    )

    # text thô mà AI trả về
    # print("\nRaw dataset output:")
    # print(raw_dataset_output)

    # Parse JSON từ output của Student
    #dữ liệu đã được Python đọc thành list/dictionary hợp lệ
    dataset_pairs = parse_dataset_json(raw_dataset_output)

    if len(dataset_pairs) == 0:
        print("\nNo valid dataset pairs generated.")
        return

    print("\nParsed dataset pairs:")
    print(json.dumps(dataset_pairs, ensure_ascii=False, indent=2))

    # Lưu dataset JSON + memory
    save_learning(
        FIELD,
        dataset_pairs
    )
    
if __name__ == "__main__":
    main()
    
    
