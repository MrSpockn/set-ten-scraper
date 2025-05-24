#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
set-ten.comの記事を自動収集・データベース更新するスケジューラスクリプト
"""

import os
import sys
import subprocess
import time
import argparse
import datetime
import logging
from pathlib import Path

# 基本設定
SCRIPT_DIR = Path(__file__).parent.absolute()
CRAWL_SCRIPT = SCRIPT_DIR / "crawl_setten.py"
SEARCH_SCRIPT = SCRIPT_DIR / "db_search.py"
LOG_DIR = SCRIPT_DIR / "logs"

# ログディレクトリがない場合は作成
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

# ロギング設定
log_file = LOG_DIR / f"crawler_{datetime.datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("setten_crawler")


def run_crawler():
    """クローラーを実行して記事を収集"""
    logger.info("クローラーを開始します...")

    try:
        start_time = time.time()

        # クローラーの実行
        result = subprocess.run(
            ["python", CRAWL_SCRIPT], capture_output=True, text=True, check=True
        )

        # 出力を表示
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)

        elapsed_time = time.time() - start_time
        logger.info(f"クローラーの実行が完了しました（経過時間: {elapsed_time:.2f}秒）")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"クローラーの実行中にエラーが発生しました: {e}")
        if e.stdout:
            logger.info(f"標準出力: {e.stdout}")
        if e.stderr:
            logger.error(f"エラー出力: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}", exc_info=True)
        return False


def display_stats():
    """データベースの統計情報を表示"""
    logger.info("データベースの統計情報を取得しています...")

    try:
        # 統計情報の取得
        result = subprocess.run(
            ["python", SEARCH_SCRIPT, "stats"],
            capture_output=True,
            text=True,
            check=True,
        )

        # 出力を表示
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"統計情報の取得中にエラーが発生しました: {e}")
        if e.stdout:
            logger.info(f"標準出力: {e.stdout}")
        if e.stderr:
            logger.error(f"エラー出力: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}", exc_info=True)
        return False


def schedule_crawl(interval_hours=24):
    """指定した時間間隔でクローラーを実行"""
    logger.info(
        f"クローラーを{interval_hours}時間おきに実行するスケジュールを開始します"
    )

    try:
        while True:
            # クローラーとデータベース統計表示の実行
            success = run_crawler()
            if success:
                display_stats()

            # 次の実行まで待機
            next_run = datetime.datetime.now() + datetime.timedelta(
                hours=interval_hours
            )
            logger.info(f"次回の実行は {next_run.strftime('%Y-%m-%d %H:%M:%S')} です")

            # 待機（1時間ごとにログを出力）
            remaining_hours = interval_hours
            while remaining_hours > 0:
                time.sleep(3600)  # 1時間待機
                remaining_hours -= 1
                if remaining_hours > 0:
                    logger.info(f"次回実行まであと{remaining_hours}時間です")

    except KeyboardInterrupt:
        logger.info("スケジューラが中断されました")
    except Exception as e:
        logger.error(f"スケジューラ実行中にエラーが発生しました: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(description="set-ten.com記事収集スケジューラ")
    parser.add_argument(
        "--run-once", action="store_true", help="一度だけクローラーを実行します"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="クローラーを実行する間隔（時間単位、デフォルト：24）",
    )

    args = parser.parse_args()

    # スクリプトパスのチェック
    if not CRAWL_SCRIPT.exists():
        logger.error(f"クローラースクリプトが見つかりません: {CRAWL_SCRIPT}")
        return 1

    if not SEARCH_SCRIPT.exists():
        logger.error(f"検索スクリプトが見つかりません: {SEARCH_SCRIPT}")
        return 1

    logger.info(f"スクリプト実行ディレクトリ: {SCRIPT_DIR}")
    logger.info(f"ログ出力先: {log_file}")

    if args.run_once:
        # 一度だけ実行
        logger.info("クローラーを一度だけ実行します")
        success = run_crawler()
        if success:
            display_stats()
    else:
        # 定期実行
        schedule_crawl(args.interval)

    return 0


if __name__ == "__main__":
    sys.exit(main())
