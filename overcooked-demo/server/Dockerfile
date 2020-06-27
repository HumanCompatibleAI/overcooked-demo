FROM python:3.7-stretch

WORKDIR /app
COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY ./static ./static
COPY ./app.py ./app.py
ENV HOST 0.0.0.0
ENV PORT 5000
EXPOSE 5000
CMD ["python", "-u", "app.py"]