# 2026-11-27 - smart-voca - 학교 서버 배포용 이미지 (Dockerfile 구성 v1.0 의 R-01~R-16)
# 빌드: docker build -t smart-voca .
# 실행: docker run -p 8080:8080 -v voca-data:/data smart-voca   → http://localhost:8080

# R-02 버전 태그가 붙은 공식 이미지
FROM python:3.13-slim

# 바이트코드(.pyc)를 쓰지 않는다: 실행 중 쓰기는 /data, /tmp 에만 (R-06). DB 위치는 DB_PATH (R-06)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DB_PATH=/data/voca.db

WORKDIR /app

# R-13 의존성 파일 먼저 복사·설치 → 소스만 바뀌면 이 층은 캐시를 다시 쓴다. R-07 설치는 빌드 때만
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# R-05 UID 10001 사용자, /data 는 그 사용자 소유 (실행 중에는 chown·설치를 하지 않는다)
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data \
    && chown 10001:10001 /data

USER 10001:10001

# R-03 0.0.0.0:8080, R-14 운영 서버(gunicorn), R-15 exec 형식
# --preload: 앱(테이블 생성·세션 키)을 마스터에서 한 번만 만든 뒤 worker 2개로 나눈다
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--preload", "--access-logfile", "-", "wsgi:app"]
