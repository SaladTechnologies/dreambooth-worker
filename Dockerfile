FROM saladtechnologies/dreambooth:sdxl

RUN pip install git+https://github.com/huggingface/peft.git

COPY src src

CMD ["python", "src/main.py"]
