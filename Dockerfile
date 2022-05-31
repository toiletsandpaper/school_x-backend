FROM python:3.8

EXPOSE 5000
EXPOSE 1337

WORKDIR /app

COPY requirements.txt /app
RUN pip3 install -r requirements.txt

COPY app/settings.py /app
COPY app/app.py /app
CMD python app.py
