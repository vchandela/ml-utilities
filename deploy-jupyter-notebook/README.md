#### Local deployment
- We use a bind mount to persist the changes in the jupyter notebook
```bash
docker build -t jupyter-notebook .
docker run -it -p 8888:8888 -v $(pwd)/notebooks:/home/jovyan jupyter-notebook
```

- Now, you can access the notebook at `http://localhost:8888` using `app.ipynb`