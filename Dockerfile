FROM saladtechnologies/dreambooth:sdxl

RUN git pull

COPY src src

CMD ["python", "src/main.py"]
