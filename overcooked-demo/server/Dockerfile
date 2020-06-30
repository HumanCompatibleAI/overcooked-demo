FROM python:3.7-stretch

ARG BUILD_ENV

WORKDIR /app
COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
RUN if [ "$BUILD_ENV" = "production" ] ; then pip install eventlet ; fi
COPY ./static ./static
COPY ./*.py ./
ENV HOST 0.0.0.0
ENV PORT 5000
EXPOSE 5000
CMD ["python", "-u", "app.py"]