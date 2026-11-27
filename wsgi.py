#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-27 - smart-voca - 운영 서버(gunicorn) 진입점: gunicorn wsgi:app
# 파일 위치: wsgi.py

# 앱 객체는 여기서만 만든다. app.py 는 팩토리(create_app)만 제공하므로 import 해도 DB 를 열지 않는다.
from app import create_app

app = create_app()
