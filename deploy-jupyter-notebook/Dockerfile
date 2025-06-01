FROM jupyter/base-notebook

COPY test.ipynb /home/jovyan/
COPY requirements.txt /home/jovyan/

# The base image runs the Jupyter server as jovyan (UID 1000).
# Docker COPY typically defaults files to root:root.
# You switch to root, fix ownership/permissions, then switch back to jovyan.
USER root
RUN chown jovyan:users /home/jovyan/test.ipynb && chmod u+w /home/jovyan/test.ipynb
USER jovyan

WORKDIR /home/jovyan
RUN pip install -r requirements.txt

EXPOSE 8888

# Provide token auth in --NotebookApp.token='<token>' for production environment
CMD ["start-notebook.py", "--NotebookApp.token=", "--NotebookApp.allow_origin='*'", "--NotebookApp.allow_remote_access=True", "--NotebookApp.disable_check_xsrf=True"]