#!/usr/bin/env python3
"""
Генератор документации из файлов проекта.

Использование:
    python generate_docs.py --output_dir helpers --debug --force

Можно запускать из корня любого Python-проекта.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Final

from onco_cola_utils import log, logerr, loginf, logsuc


# === Конфигурация файлов для генерации ===
FILES_CONFIG: Final[dict[str, dict[str, Any]]] = {
    "BOT.txt": {
        "desc": "Телеграм бот тиктока",
        "paths": {
            "main.py": "src/main.py",
            "config.py": "src/config.py",
            "filters.py": "src/filters.py",
            "downloader.py": "src/handlers/downloader.py",
            "tiktok-service.py": "src/services/tiktok_downloader.py",
        }
    },
}


class DocumentationGenerator:
    """Генератор документации из файлов проекта."""
    
    def __init__(self, output_dir: Path, debug: bool = False, force: bool = False) -> None:
        self.output_dir = output_dir
        self.debug = debug
        self.force = force
    
    def generate(self) -> tuple[int, int]:
        """
        Запускает генерацию документации.

        Returns:
            Кортеж (успешно, ошибок)
        """
        loginf("Начинаю генерацию документации...")
        loginf(f"Выходная директория: {self.output_dir.absolute()}")
        
        # Создаем директорию для выходных файлов
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        error_count = 0
        
        # Обрабатываем каждый выходной файл
        for output_filename, config in FILES_CONFIG.items():
            desc = config.get("desc", "")
            files_mapping = config.get("paths", {})
            
            if not files_mapping:
                log(f"⚠️  Пропускаю {output_filename} — нет файлов для обработки")
                continue
            
            output_path = self.output_dir / output_filename
            
            # Проверяем существование файла
            if output_path.exists() and not self.force:
                confirm = input(
                    f"⚠️  Файл {output_path} уже существует. Перезаписать? (y/N): "
                )
                if confirm.lower() != 'y':
                    log(f"⏭️  Пропускаю {output_filename}")
                    continue
            
            try:
                self._generate_file(output_path, desc, files_mapping)
                logsuc(f"Успешно создан: {output_filename}")
                success_count += 1
            except FileNotFoundError as e:
                logerr(f"Ошибка при создании {output_filename}: {e}")
                error_count += 1
            except Exception as e:
                logerr(f"Ошибка при создании {output_filename}: {e}")
                error_count += 1
        
        # Итоговая статистика
        loginf("\n" + "=" * 60)
        loginf("Завершение генерации документации")
        loginf(f"Успешно: {success_count}")
        loginf(f"Ошибок: {error_count}")
        
        return success_count, error_count
    
    def _generate_file(
        self,
        output_path: Path,
        description: str,
        files_mapping: dict[str, str]
    ) -> None:
        """
        Генерирует один выходной файл из указанных исходных файлов.

        Args:
            output_path: Путь к выходному файлу
            description: Описание секции
            files_mapping: Словарь {имя_файла: путь_к_файлу}
        """
        content_parts: list[str] = []
        
        for display_name, file_path in files_mapping.items():
            file_full_path = Path(file_path)
            
            if self.debug:
                log(f"📄 Обрабатываю: {display_name} → {file_full_path}")
            
            try:
                file_content = self._read_file(file_full_path)
                block = self._format_file_block(description, file_path, file_content)
                content_parts.append(block)
            
            except FileNotFoundError:
                logerr(f"Файл не найден: {file_full_path}")
                raise
            except Exception as e:
                logerr(f"Ошибка чтения {file_full_path}: {e}")
                raise
        
        final_content = '\n\n'.join(content_parts)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        if self.debug:
            log(f"📝 Записано {len(content_parts)} файлов в {output_path}")
    
    @staticmethod
    def _read_file(file_path: Path) -> str:
        """Читает содержимое файла."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def _format_file_block(description: str, file_path: str, content: str) -> str:
        """
        Форматирует блок для одного файла.

        Формат:
        #
        # Тут находятся модели, используемые в APIView
        # Расположение: apps/calls/models/call.py
        #

        from django.db import models
        ...
        """
        lines = ["#"]
        if description:
            lines.append(f"# {description}")
        lines.append(f"# Расположение: {file_path}")
        lines.append("#")
        header = "\n".join(lines)
        return f"{header}\n\n{content}"


def create_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Генерирует документацию из указанных файлов проекта',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
    python generate_docs.py
    python generate_docs.py --output_dir docs --debug
    python generate_docs.py --force --output_dir helpers
        """
    )
    
    parser.add_argument(
        '--output_dir',
        type=str,
        default='helpers',
        help='Директория для выходных файлов (по умолчанию: helpers)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Включить режим отладки'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Перезаписать существующие файлы без подтверждения'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser


def main() -> int:
    """Точка входа в приложение."""
    parser = create_parser()
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    
    generator = DocumentationGenerator(
        output_dir=output_dir,
        debug=args.debug,
        force=args.force
    )
    
    success_count, error_count = generator.generate()
    
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
