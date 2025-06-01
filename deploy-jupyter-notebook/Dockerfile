FROM jupyter/base-notebook

COPY requirements.txt /home/jovyan/

WORKDIR /home/jovyan
RUN pip install -r requirements.txt

EXPOSE 8888

# Provide token auth in --NotebookApp.token='<token>' for production environment
CMD ["start-notebook.py", "--NotebookApp.token=", "--NotebookApp.allow_origin='*'", "--NotebookApp.allow_remote_access=True", "--NotebookApp.disable_check_xsrf=True"]