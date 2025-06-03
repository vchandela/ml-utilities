FROM jupyter/base-notebook

COPY notebooks/test.ipynb /home/jovyan/
COPY requirements.txt /home/jovyan/

WORKDIR /home/jovyan
RUN pip install -r requirements.txt

EXPOSE 8888