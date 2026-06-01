# This Python file uses the following encoding: utf-8
# @brief    Continue to breed (继续育成)
# @author   jackyhwei
# @note     draft version without full test
# github    https://github.com/roarhill/oas
from pydantic import BaseModel, Field

from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase

class BreedConfig(BaseModel):
    continue_breed_times : int = Field(title='continue to breed time', default=100, description='continue_to_breed_times_help')

class ContinueBreed(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    breed_config: BreedConfig = Field(default_factory=BreedConfig)
