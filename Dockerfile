FROM python:3.12

WORKDIR /fast_chat

COPY /pyproject.toml /fast_chat


RUN pip3 install -U poetry
RUN poetry config virtualenvs.path --unset
RUN poetry config virtualenvs.in-project false
RUN poetry install  --no-ansi --no-root

COPY . .

RUN chmod a+x /fast_chat/scripts/*.sh