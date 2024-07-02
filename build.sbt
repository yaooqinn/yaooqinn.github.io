ThisBuild / scalaVersion := "2.13.14"
ThisBuild / organization := "io.github.yaooqinn"

lazy val spark = (project in file("./spark"))
  .settings(
    name := "spark",
    libraryDependencies += "org.apache.spark" %% "spark-sql" % "4.0.0-preview1" % Compile
  )