FROM saladtechnologies/dreambooth:sdxl

COPY src src

CMD ["python", "src/main.py"]
