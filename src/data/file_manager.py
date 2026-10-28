#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - smart-voca - 파일 관리
# 파일 위치: src/data/file_manager.py

import json
import csv
import os
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FileManager:
    """파일 I/O 관리"""

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def read_csv(self, filename: str) -> List[Dict]:
        """CSV 파일 읽기"""
        filepath = self.data_dir / filename

        if not filepath.exists():
            logger.warning(f"파일이 없습니다: {filepath}")
            return []

        try:
            data = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            logger.info(f"CSV 로드 완료: {filepath} ({len(data)}행)")
            return data
        except Exception as e:
            logger.error(f"CSV 읽기 오류: {e}")
            raise

    def write_csv(self, filename: str, data: List[Dict]) -> bool:
        """CSV 파일 쓰기"""
        filepath = self.data_dir / filename

        if not data:
            logger.warning("저장할 데이터가 없습니다")
            return False

        try:
            keys = data[0].keys()
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
            logger.info(f"CSV 저장 완료: {filepath} ({len(data)}행)")
            return True
        except Exception as e:
            logger.error(f"CSV 쓰기 오류: {e}")
            raise

    def append_csv(self, filename: str, data: Dict) -> bool:
        """CSV 파일에 행 추가"""
        filepath = self.data_dir / filename

        try:
            # 파일이 없으면 새로 생성
            if not filepath.exists():
                self.write_csv(filename, [data])
                return True

            # 기존 데이터 읽기
            existing = self.read_csv(filename)
            existing.append(data)
            self.write_csv(filename, existing)
            return True
        except Exception as e:
            logger.error(f"CSV append 오류: {e}")
            raise

    def read_json(self, filename: str) -> Dict:
        """JSON 파일 읽기"""
        filepath = self.data_dir / filename

        if not filepath.exists():
            logger.warning(f"파일이 없습니다: {filepath}")
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"JSON 로드 완료: {filepath}")
            return data
        except Exception as e:
            logger.error(f"JSON 읽기 오류: {e}")
            raise

    def write_json(self, filename: str, data: Dict) -> bool:
        """JSON 파일 쓰기"""
        filepath = self.data_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"JSON 저장 완료: {filepath}")
            return True
        except Exception as e:
            logger.error(f"JSON 쓰기 오류: {e}")
            raise

    def backup_file(self, filename: str) -> bool:
        """파일 백업"""
        filepath = self.data_dir / filename

        if not filepath.exists():
            return False

        try:
            backup_path = self.data_dir / f"{filename}.bak"
            import shutil
            shutil.copy2(filepath, backup_path)
            logger.info(f"백업 생성: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"백업 오류: {e}")
            raise

    def delete_file(self, filename: str) -> bool:
        """파일 삭제"""
        filepath = self.data_dir / filename

        if not filepath.exists():
            return False

        try:
            filepath.unlink()
            logger.info(f"파일 삭제: {filepath}")
            return True
        except Exception as e:
            logger.error(f"삭제 오류: {e}")
            raise

    def file_exists(self, filename: str) -> bool:
        """파일 존재 여부"""
        return (self.data_dir / filename).exists()

    def ensure_directories(self) -> None:
        """필수 디렉토리 생성"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
