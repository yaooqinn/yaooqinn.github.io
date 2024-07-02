package io.github.yaooqinn.spark.tools

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Paths, StandardOpenOption}

import org.apache.spark.config.ConfigEntryWrapper
import org.apache.spark.config.ConfigEntryWrapper.isConfigEntry
import org.apache.spark.sql.internal.SQLConf

object InternalConfigs {

  def main(args: Array[String]): Unit = {
    val configs = SQLConf.getClass.getDeclaredFields
      .filter(isConfigEntry)
      .map { f =>
        f.setAccessible(true)
        ConfigEntryWrapper.apply(f.get(SQLConf))
      }
      .filter(e => e.entry != null && !e.entry.isPublic)
    val path = Paths.get(System.getProperty("user.dir"), "spark", "docs", "configs", "internal_configs.rst")
    val writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)

    writer.write("SQL Internal Configurations\n---------------------------\n\n")
    writer.write(s"The following configurations are internal to Spark and are not intended to be modified by users. Total (${configs.length})\n\n")
    val configGrp = configs.groupBy(_.entry.key.split('.')(2))
    configGrp.foreach { case (grp, entries) =>
      writer.write(s"\n${grp.capitalize}(${entries.length})\n${"~" * (grp.length + 2 + entries.length.toString.length)}\n\n")
      writer.write(s".. list-table:: ${grp.capitalize}\n")
      writer.write("   :header-rows: 1\n")
      writer.write("\n   * - Key\n     - Since\n     - Default\n     - Description\n")
      entries.sortBy(_.entry.version).foreach { entry =>
        val key = entry.entry.key
        val doc = {
          val fields = entry.entry.doc.split("\n")
          if (fields.length > 1) {
            fields.mkString("| ", "\n       | ", "")
          } else {
            fields.head
          }
        }
        val defaultValue = entry.entry.defaultValueString
        val version = entry.entry.version
        writer.write(s"   * - $key\n     - $version\n     - $defaultValue\n     - $doc\n")
      }
    }

    writer.close()
  }
}
