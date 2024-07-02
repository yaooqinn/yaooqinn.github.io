package org.apache.spark.config

import java.lang.reflect.Field

import org.apache.spark.internal.config.ConfigEntry

class ConfigEntryWrapper[T](val entry: ConfigEntry[T]) {

}

object ConfigEntryWrapper {
  def apply[T](entry: Any): ConfigEntryWrapper[T] = {
    new ConfigEntryWrapper(entry.asInstanceOf[ConfigEntry[T]])
  }

  def isConfigEntry(f: Field): Boolean = classOf[ConfigEntry[_]].isAssignableFrom(f.getType)

}


