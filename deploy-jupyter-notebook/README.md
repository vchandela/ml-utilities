#### Local deployment
- Remove this line `COPY notebooks/test.ipynb /home/jovyan/` from the Dockerfile.
- We use a bind mount to persist the changes in the jupyter notebook
```bash
docker build -t jupyter-notebook .
docker run -it -p 8888:8888 -v $(pwd)/notebooks:/home/jovyan jupyter-notebook
```

- Now, you can access the notebook at `http://localhost:8888` using `app.ipynb`. Just change the `url` for local env.