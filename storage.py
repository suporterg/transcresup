import json
import os
from typing import List, Dict
from datetime import datetime, timedelta
import traceback
import logging
import redis

class StorageHandler:
    def __init__(self):
        # Configuração de logger
        self.logger = logging.getLogger("StorageHandler")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("StorageHandler inicializado.")

        # Conexão com o Redis
        self.redis = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6380)),
            db=0,
            decode_responses=True
        )

        # Retenção de logs e backups
        self.log_retention_hours = int(os.getenv('LOG_RETENTION_HOURS', 48))
        self.backup_retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', 7))

    def _get_redis_key(self, key):
        return f"transcrevezap:{key}"

    def add_log(self, level: str, message: str, metadata: dict = None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "metadata": json.dumps(metadata) if metadata else None
        }
        self.redis.lpush(self._get_redis_key("logs"), json.dumps(log_entry))
        self.redis.ltrim(self._get_redis_key("logs"), 0, 999)  # Manter apenas os últimos 1000 logs
        self.logger.log(getattr(logging, level.upper(), logging.INFO), f"{message} | Metadata: {metadata}")

    def get_allowed_groups(self) -> List[str]:
        return self.redis.smembers(self._get_redis_key("allowed_groups"))

    def add_allowed_group(self, group: str):
        self.redis.sadd(self._get_redis_key("allowed_groups"), group)

    def remove_allowed_group(self, group: str):
        self.redis.srem(self._get_redis_key("allowed_groups"), group)

    def get_blocked_users(self) -> List[str]:
        return self.redis.smembers(self._get_redis_key("blocked_users"))

    def add_blocked_user(self, user: str):
        self.redis.sadd(self._get_redis_key("blocked_users"), user)

    def remove_blocked_user(self, user: str):
        self.redis.srem(self._get_redis_key("blocked_users"), user)

    def get_statistics(self) -> Dict:
        total_processed = int(self.redis.get(self._get_redis_key("total_processed")) or 0)
        last_processed = self.redis.get(self._get_redis_key("last_processed"))
        daily_count = json.loads(self.redis.get(self._get_redis_key("daily_count")) or "{}")
        group_count = json.loads(self.redis.get(self._get_redis_key("group_count")) or "{}")
        user_count = json.loads(self.redis.get(self._get_redis_key("user_count")) or "{}")
        error_count = int(self.redis.get(self._get_redis_key("error_count")) or 0)
        success_rate = float(self.redis.get(self._get_redis_key("success_rate")) or 100.0)

        return {
            "total_processed": total_processed,
            "last_processed": last_processed,
            "stats": {
                "daily_count": daily_count,
                "group_count": group_count,
                "user_count": user_count,
                "error_count": error_count,
                "success_rate": success_rate,
            }
        }

    def can_process_message(self, remote_jid):
        try:
            allowed_groups = self.get_allowed_groups()
            blocked_users = self.get_blocked_users()

            if remote_jid in blocked_users:
                return False
            if "@g.us" in remote_jid and remote_jid not in allowed_groups:
                return False

            return True
        except Exception as e:
            self.logger.error(f"Erro ao verificar se pode processar mensagem: {e}")
            return False

    def record_processing(self, remote_jid):
        try:
            # Incrementar total processado
            self.redis.incr(self._get_redis_key("total_processed"))

            # Atualizar último processamento
            self.redis.set(self._get_redis_key("last_processed"), datetime.now().isoformat())

            # Atualizar contagem diária
            today = datetime.now().strftime("%Y-%m-%d")
            daily_count = json.loads(self.redis.get(self._get_redis_key("daily_count")) or "{}")
            daily_count[today] = daily_count.get(today, 0) + 1
            self.redis.set(self._get_redis_key("daily_count"), json.dumps(daily_count))

            # Atualizar contagem de grupo ou usuário
            if "@g.us" in remote_jid:
                group_count = json.loads(self.redis.get(self._get_redis_key("group_count")) or "{}")
                group_count[remote_jid] = group_count.get(remote_jid, 0) + 1
                self.redis.set(self._get_redis_key("group_count"), json.dumps(group_count))
            else:
                user_count = json.loads(self.redis.get(self._get_redis_key("user_count")) or "{}")
                user_count[remote_jid] = user_count.get(remote_jid, 0) + 1
                self.redis.set(self._get_redis_key("user_count"), json.dumps(user_count))

            # Atualizar taxa de sucesso
            total = int(self.redis.get(self._get_redis_key("total_processed")) or 0)
            errors = int(self.redis.get(self._get_redis_key("error_count")) or 0)
            success_rate = ((total - errors) / total) * 100 if total > 0 else 100
            self.redis.set(self._get_redis_key("success_rate"), success_rate)

        except Exception as e:
            self.logger.error(f"Erro ao registrar processamento: {e}")

    def record_error(self):
        self.redis.incr(self._get_redis_key("error_count"))

    def clean_old_logs(self):
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.log_retention_hours)
            logs = self.redis.lrange(self._get_redis_key("logs"), 0, -1)
            for log in logs:
                log_entry = json.loads(log)
                if datetime.fromisoformat(log_entry["timestamp"]) < cutoff_time:
                    self.redis.lrem(self._get_redis_key("logs"), 0, log)
                else:
                    break  # Assumindo que os logs estão ordenados por tempo
        except Exception as e:
            self.logger.error(f"Erro ao limpar logs antigos: {e}")

    def backup_data(self):
        try:
            data = {
                "allowed_groups": list(self.get_allowed_groups()),
                "blocked_users": list(self.get_blocked_users()),
                "statistics": self.get_statistics(),
            }
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_key = f"backup:{timestamp}"
            self.redis.set(backup_key, json.dumps(data))
            self.redis.expire(backup_key, self.backup_retention_days * 24 * 60 * 60)  # Expira após os dias de retenção
        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")

    def clean_old_backups(self):
        try:
            for key in self.redis.scan_iter("backup:*"):
                if self.redis.ttl(key) <= 0:
                    self.redis.delete(key)
        except Exception as e:
            self.logger.error(f"Erro ao limpar backups antigos: {e}")