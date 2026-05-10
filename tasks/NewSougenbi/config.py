# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, time

from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig


class NewSougenbiClass(str, Enum):
    GREED = '贪'
    Anger = '嗔'
    Foolery = '痴'

class NewSougenbiConfig(ConfigBase):
    new_sougenbi_class: NewSougenbiClass = Field(default=NewSougenbiClass.Foolery)
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30), description='limit_time_help') # type: ignore
    # 限制次数
    limit_count: int = Field(default=30, description='limit_count_help')

    # 加成
    buff_enable: bool = Field(default=False)
    # 是否点击金币50buff
    buff_gold_50_click: bool = Field(default=False, description='')
    # 是否点击金币100buff
    buff_gold_100_click: bool = Field(default=False, description='')
    # 是否点击经验50buff
    buff_exp_50_click: bool = Field(default=False, description='')
    # 是否点击经验100buff
    buff_exp_100_click: bool = Field(default=False, description='')


class NewSougenbi(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    new_sougenbi_config: NewSougenbiConfig = Field(default_factory=NewSougenbiConfig)
    general_battle_config: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)

