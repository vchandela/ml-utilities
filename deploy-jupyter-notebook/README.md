#### Local deployment
```bash
docker build -t jupyter-notebook .
docker run -p 8888:8888 jupyter-notebook
```

- Now, you can access the notebook at `http://localhost:8888` using `app.ipynb`