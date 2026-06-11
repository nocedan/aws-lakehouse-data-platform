FROM public.ecr.aws/lambda/python:3.12

# pg_restore/psql client; prefer 17 (matches the RDS engine), fall back to 16
RUN dnf install -y postgresql17 || dnf install -y postgresql16; dnf clean all

# RDS CA bundle so the handler can connect with sslmode=verify-full
ADD https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem /certs/global-bundle.pem
RUN chmod a+r /certs/global-bundle.pem

COPY handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_handler"]
