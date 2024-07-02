SQL Internal Configurations
---------------------------

The following configurations are internal to Spark and are not intended to be modified by users. Total (290)


Optimizer(34)
~~~~~~~~~~~~~

.. list-table:: Optimizer
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.optimizer.pullHintsIntoSubqueries
     - 
     - true
     - Pull hints into subqueries in EliminateResolvedHint if enabled.
   * - spark.sql.optimizer.maxIterations
     - 2.0.0
     - 100
     - The max number of iterations the optimizer runs.
   * - spark.sql.optimizer.inSetConversionThreshold
     - 2.0.0
     - 10
     - The threshold of set size for InSet conversion.
   * - spark.sql.optimizer.metadataOnly
     - 2.1.1
     - false
     - When true, enable the metadata-only query optimization that use the table's metadata to produce the partition columns instead of table scans. It applies when all the columns scanned are partition columns and the query has an aggregate operator that satisfies distinct semantics. By default the optimization is disabled, and deprecated as of Spark 3.0 since it may return incorrect results when the files are empty, see also SPARK-26709.It will be removed in the future releases. If you must use, use 'SparkSessionExtensions' instead to inject it as a custom rule.
   * - spark.sql.optimizer.replaceExceptWithFilter
     - 2.3.0
     - true
     - When true, the apply function of the rule verifies whether the right node of the except operation is of type Filter or Project followed by Filter. If yes, the rule further verifies 1) Excluding the filter operations from the right (as well as the left node, if any) on the top, whether both the nodes evaluates to a same result. 2) The left and right nodes don't contain any SubqueryExpressions. 3) The output column names of the left node are distinct. If all the conditions are met, the rule will replace the except operation with a Filter by flipping the filter condition(s) of the right node.
   * - spark.sql.optimizer.nestedSchemaPruning.enabled
     - 2.4.1
     - true
     - Prune nested fields from a logical relation's output which are unnecessary in satisfying a query. This optimization allows columnar file format readers to avoid reading unnecessary nested column data. Currently Parquet and ORC are the data sources that implement this optimization.
   * - spark.sql.optimizer.inSetSwitchThreshold
     - 3.0.0
     - 400
     - Configures the max set size in InSet for which Spark will generate code with switch statements. This is applicable only to bytes, shorts, ints, dates.
   * - spark.sql.optimizer.dynamicPartitionPruning.useStats
     - 3.0.0
     - true
     - When true, distinct count statistics will be used for computing the data size of the partitioned table after dynamic partition pruning, in order to evaluate if it is worth adding an extra subquery as the pruning filter if broadcast reuse is not applicable.
   * - spark.sql.optimizer.dynamicPartitionPruning.fallbackFilterRatio
     - 3.0.0
     - 0.5
     - When statistics are not available or configured not to be used, this config will be used as the fallback filter ratio for computing the data size of the partitioned table after dynamic partition pruning, in order to evaluate if it is worth adding an extra subquery as the pruning filter if broadcast reuse is not applicable.
   * - spark.sql.optimizer.dynamicPartitionPruning.reuseBroadcastOnly
     - 3.0.0
     - true
     - When true, dynamic partition pruning will only apply when the broadcast exchange of a broadcast hash join operation can be reused as the dynamic pruning filter.
   * - spark.sql.optimizer.nestedPredicatePushdown.supportedFileSources
     - 3.0.0
     - parquet,orc
     - A comma-separated list of data source short names or fully qualified data source implementation class names for which Spark tries to push down predicates for nested columns and/or names containing `dots` to data sources. This configuration is only effective with file-based data sources in DSv1. Currently, Parquet and ORC implement both optimizations. The other data sources don't support this feature yet. So the default value is 'parquet,orc'.
   * - spark.sql.optimizer.serializer.nestedSchemaPruning.enabled
     - 3.0.0
     - true
     - Prune nested fields from object serialization operator which are unnecessary in satisfying a query. This optimization allows object serializers to avoid executing unnecessary nested expressions.
   * - spark.sql.optimizer.expression.nestedPruning.enabled
     - 3.0.0
     - true
     - Prune nested fields from expressions in an operator which are unnecessary in satisfying a query. Note that this optimization doesn't prune nested fields from physical data source scanning. For pruning nested fields from scanning, please use `spark.sql.optimizer.nestedSchemaPruning.enabled` config.
   * - spark.sql.optimizer.disableHints
     - 3.1.0
     - false
     - When true, the optimizer will disable user-specified hints that are additional directives for better planning of a query.
   * - spark.sql.optimizer.canChangeCachedPlanOutputPartitioning
     - 3.2.0
     - false
     - Whether to forcibly enable some optimization rules that can change the output partitioning of a cached query when executing it for caching. If it is set to true, queries may need an extra shuffle to read the cached data. This configuration is disabled by default. The optimization rule enabled by this configuration is spark.sql.adaptive.applyFinalStageShuffleOptimizations.
   * - spark.sql.optimizer.decorrelateInnerQuery.enabled
     - 3.2.0
     - true
     - Decorrelate inner query by eliminating correlated references and build domain joins.
   * - spark.sql.optimizer.optimizeOneRowRelationSubquery
     - 3.2.0
     - true
     - When true, the optimizer will inline subqueries with OneRowRelation as leaf nodes.
   * - spark.sql.optimizer.propagateDistinctKeys.enabled
     - 3.3.0
     - true
     - When true, the query optimizer will propagate a set of distinct attributes from the current node and use it to optimize query.
   * - spark.sql.optimizer.plannedWrite.enabled
     - 3.4.0
     - true
     - When set to true, Spark optimizer will add logical sort operators to V1 write commands if needed so that `FileFormatWriter` does not need to insert physical sorts.
   * - spark.sql.optimizer.expressionProjectionCandidateLimit
     - 3.4.0
     - 100
     - The maximum number of the candidate of output expressions whose alias are replaced. It can preserve the output partitioning and ordering. Negative value means disable this optimization.
   * - spark.sql.optimizer.decorrelateSetOps.enabled
     - 3.4.0
     - true
     - Decorrelate subqueries with correlation under set operators.
   * - spark.sql.optimizer.optimizeOneRowRelationSubquery.alwaysInline
     - 3.4.0
     - true
     - When true, the optimizer will always inline single row subqueries even if it causes extra duplication. It only takes effect when spark.sql.optimizer.optimizeOneRowRelationSubquery is set to true.
   * - spark.sql.optimizer.windowGroupLimitThreshold
     - 3.5.0
     - 1000
     - Threshold for triggering `InsertWindowGroupLimit`. 0 means the output results is empty. -1 means disabling the optimization.
   * - spark.sql.optimizer.decorrelateSubqueryLegacyIncorrectCountHandling.enabled
     - 3.5.0
     - false
     - If enabled, revert to legacy incorrect behavior for certain subqueries with COUNT or similar aggregates: see SPARK-43098.
   * - spark.sql.optimizer.decorrelateLimit.enabled
     - 4.0.0
     - true
     - Decorrelate subqueries with correlation under LIMIT.
   * - spark.sql.optimizer.decorrelateOffset.enabled
     - 4.0.0
     - false
     - Decorrelate subqueries with correlation under LIMIT with OFFSET.
   * - spark.sql.optimizer.decorrelateExistsSubqueryLegacyIncorrectCountHandling.enabled
     - 4.0.0
     - false
     - If enabled, revert to legacy incorrect behavior for certain EXISTS/IN subqueries with COUNT or similar aggregates.
   * - spark.sql.optimizer.decorrelateSubqueryPreventConstantHoldingForCountBug.enabled
     - 4.0.0
     - true
     - If enabled, prevents constant folding in subqueries that contain a COUNT-bug-susceptible Aggregate.
   * - spark.sql.optimizer.pullOutNestedDataOuterRefExpressions.enabled
     - 4.0.0
     - true
     - Handle correlation over nested data extract expressions by pulling out the expression into the outer plan. This enables correlation on map attributes for example.
   * - spark.sql.optimizer.wrapExistsInAggregateFunction
     - 4.0.0
     - true
     - When true, the optimizer will wrap newly introduced `exists` attributes in an aggregate function to ensure that Aggregate nodes preserve semantic invariant that each variable among agg expressions appears either in grouping expressions or belongs to and aggregate function.
   * - spark.sql.optimizer.decorrelateJoinPredicate.enabled
     - 4.0.0
     - true
     - Decorrelate scalar and lateral subqueries with correlated references in join predicates. This configuration is only effective when 'spark.sql.optimizer.decorrelateInnerQuery.enabled' is true.
   * - spark.sql.optimizer.decorrelatePredicateSubqueriesInJoinPredicate.enabled
     - 4.0.0
     - true
     - Decorrelate predicate (in and exists) subqueries with correlated references in join predicates.
   * - spark.sql.optimizer.optimizeUncorrelatedInSubqueriesInJoinCondition.enabled
     - 4.0.0
     - true
     - When true, optimize uncorrelated IN subqueries in join predicates by rewriting them to joins. This interacts with spark.sql.legacy.nullInEmptyListBehavior because it can rewrite IN predicates.
   * - spark.sql.optimizer.excludeSubqueryRefsFromRemoveRedundantAliases.enabled
     - 4.0.0
     - true
     - When true, exclude the references from the subquery expressions (in, exists, etc.) while removing redundant aliases.

DefaultSizeInBytes(1)
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: DefaultSizeInBytes
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.defaultSizeInBytes
     - 1.1.0
     - 9223372036854775807b
     - The default table size used in query planning. By default, it is set to Long.MaxValue which is larger than `spark.sql.autoBroadcastJoinThreshold` to be more conservative. That is to say by default the optimizer will not choose to broadcast a table unless it knows for sure its size is small enough.

Cbo(2)
~~~~~~

.. list-table:: Cbo
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.cbo.joinReorder.card.weight
     - 2.2.0
     - 0.7
     - The weight of the ratio of cardinalities (number of rows) in the cost comparison function. The ratio of sizes in bytes has weight 1 - this value. The weighted geometric mean of these ratios is used to decide which of the candidate plans will be chosen by the CBO.
   * - spark.sql.cbo.starJoinFTRatio
     - 2.2.0
     - 0.9
     - Specifies the upper limit of the ratio between the largest fact tables for a star join to be considered. 

JsonGenerator(1)
~~~~~~~~~~~~~~~~

.. list-table:: JsonGenerator
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.jsonGenerator.writeNullIfWithDefaultValue
     - 3.4.0
     - true
     - When true, when writing NULL values to columns of JSON tables with explicit DEFAULT values using INSERT, UPDATE, or MERGE commands, never skip writing the NULL values to storage, overriding spark.sql.jsonGenerator.ignoreNullFields or the ignoreNullFields option. This can be useful to enforce that inserted NULL values are present in storage to differentiate from missing data.

RequireAllClusterKeysForDistribution(1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: RequireAllClusterKeysForDistribution
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.requireAllClusterKeysForDistribution
     - 3.3.0
     - false
     - When true, the planner requires all the clustering keys as the partition keys (with same ordering) of the children, to eliminate the shuffle for the operator that requires its children be clustered distributed, such as AGGREGATE and WINDOW node. This is to avoid data skews which can lead to significant performance regression if shuffle is eliminated.

PlanChangeValidation(1)
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: PlanChangeValidation
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.planChangeValidation
     - 3.4.0
     - false
     - If true, Spark will validate all the plan changes made by analyzer/optimizer and other catalyst rules, to make sure every rule returns a valid plan

DataframeCache(1)
~~~~~~~~~~~~~~~~~

.. list-table:: DataframeCache
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.dataframeCache.logLevel
     - 4.0.0
     - trace
     - Configures the log level of Dataframe cache operations, including adding and removing entries from Dataframe cache, hit and miss on cache application. The default log level is 'trace'. This log should only be used for debugging purposes and not in the production environment, since it generates a large amount of logs.

ThriftServer(1)
~~~~~~~~~~~~~~~

.. list-table:: ThriftServer
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.thriftServer.incrementalCollect
     - 2.0.3
     - false
     - When true, enable incremental collection for execution in Thrift Server.

Execution(13)
~~~~~~~~~~~~~

.. list-table:: Execution
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.execution.sortBeforeRepartition
     - 2.1.4
     - true
     - When perform a repartition following a shuffle, the output row ordering would be nondeterministic. If some downstream stages fail and some tasks of the repartition stage retry, these tasks may generate different data, and that can lead to correctness issues. Turn on this config to insert a local sort before actually doing repartition to generate consistent repartition results. The performance of repartition() may go down since we insert extra local sort before it.
   * - spark.sql.execution.useObjectHashAggregateExec
     - 2.2.0
     - true
     - Decides if we use ObjectHashAggregateExec
   * - spark.sql.execution.rangeExchange.sampleSizePerPartition
     - 2.3.0
     - 100
     - Number of points to sample per partition in order to determine the range boundaries for range partitioning, typically used in global sorting (without limit).
   * - spark.sql.execution.removeRedundantSorts
     - 2.4.8
     - true
     - Whether to remove redundant physical sort node
   * - spark.sql.execution.reuseSubquery
     - 3.0.0
     - true
     - When true, the planner will try to find out duplicated subqueries and re-use them.
   * - spark.sql.execution.pandas.convertToArrowArraySafely
     - 3.0.0
     - false
     - When true, Arrow will perform safe type conversion when converting Pandas.Series to Arrow array during serialization. Arrow will raise errors when detecting unsafe type conversion like overflow. When false, disabling Arrow's type check and do type conversions anyway. This config only works for Arrow 0.11.0+.
   * - spark.sql.execution.fastFailOnFileFormatOutput
     - 3.0.2
     - false
     - Whether to fast fail task execution when writing output to FileFormat datasource. If this is enabled, in `FileFormatWriter` we will catch `FileAlreadyExistsException` and fast fail output task without further task retry. Only enabling this if you know the `FileAlreadyExistsException` of the output task is unrecoverable, i.e., further task attempts won't be able to success. If the `FileAlreadyExistsException` might be recoverable, you should keep this as disabled and let Spark to retry output tasks. This is disabled by default.
   * - spark.sql.execution.removeRedundantProjects
     - 3.1.0
     - true
     - Whether to remove redundant project exec node based on children's output and ordering requirement.
   * - spark.sql.execution.broadcastHashJoin.outputPartitioningExpandLimit
     - 3.1.0
     - 8
     - The maximum number of partitionings that a HashPartitioning can be expanded to. This configuration is applicable only for BroadcastHashJoin inner joins and can be set to '0' to disable this feature.
   * - spark.sql.execution.replaceHashWithSortAgg
     - 3.3.0
     - false
     - Whether to replace hash aggregate node with sort aggregate based on children's ordering
   * - spark.sql.execution.usePartitionEvaluator
     - 3.5.0
     - false
     - When true, use PartitionEvaluator to execute SQL operators.
   * - spark.sql.execution.arrow.useLargeVarTypes
     - 3.5.0
     - false
     - When using Apache Arrow, use large variable width vectors for string and binary types. Regular string and binary types have a 2GiB limit for a column in a single record batch. Large variable types remove this limitation at the cost of higher memory usage per value. Note that this only works for DataFrame.mapInArrow.
   * - spark.sql.execution.pyspark.python
     - 3.5.0
     - <undefined>
     - Python binary executable to use for PySpark in executors when running Python UDF, pandas UDF and pandas function APIs.If not set, it falls back to 'spark.pyspark.python' by default.

Legacy(79)
~~~~~~~~~~

.. list-table:: Legacy
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.legacy.literal.pickMinimumPrecision
     - 2.3.3
     - true
     - When integral literal is used in decimal operations, pick a minimum precision required by the literal if this config is true, to make the resulting precision and/or scale smaller. This can reduce the possibility of precision lose and/or overflow.
   * - spark.sql.legacy.sizeOfNull
     - 2.4.0
     - true
     - If it is set to false, or spark.sql.ansi.enabled is true, then size of null returns null. Otherwise, it returns -1, which was inherited from Hive.
   * - spark.sql.legacy.replaceDatabricksSparkAvro.enabled
     - 2.4.0
     - true
     - If it is set to true, the data source provider com.databricks.spark.avro is mapped to the built-in but external Avro data source module for backward compatibility.
   * - spark.sql.legacy.setopsPrecedence.enabled
     - 2.4.0
     - false
     - When set to true and the order of evaluation is not specified by parentheses, the set operations are performed from left to right as they appear in the query. When set to false and order of evaluation is not specified by parentheses, INTERSECT operations are performed before any UNION, EXCEPT and MINUS operations.
   * - spark.sql.legacy.execution.pandas.groupedMap.assignColumnsByName
     - 2.4.1
     - true
     - When true, columns will be looked up by name if labeled with a string and fallback to use position if not. When false, a grouped map Pandas UDF will assign columns from the returned Pandas DataFrame based on position, regardless of column label type. This configuration will be deprecated in future releases.
   * - spark.sql.legacy.parser.havingWithoutGroupByAsWhere
     - 2.4.1
     - false
     - If it is set to true, the parser will treat HAVING without GROUP BY as a normal WHERE, which does not follow SQL standard.
   * - spark.sql.legacy.mssqlserver.numericMapping.enabled
     - 2.4.5
     - false
     - When true, use legacy MsSqlServer TINYINT, SMALLINT and REAL type mapping.
   * - spark.sql.legacy.exponentLiteralAsDecimal.enabled
     - 3.0.0
     - false
     - When set to true, a literal with an exponent (e.g. 1E-30) would be parsed as Decimal rather than Double.
   * - spark.sql.legacy.allowNegativeScaleOfDecimal
     - 3.0.0
     - false
     - When set to true, negative scale of Decimal type is allowed. For example, the type of number 1E10BD under legacy mode is DecimalType(2, -9), but is Decimal(11, 0) in non legacy mode.
   * - spark.sql.legacy.bucketedTableScan.outputOrdering
     - 3.0.0
     - false
     - When true, the bucketed table scan will list files during planning to figure out the output ordering, which is expensive and may make the planning quite slow.
   * - spark.sql.legacy.json.allowEmptyString.enabled
     - 3.0.0
     - false
     - When set to true, the parser of JSON data source treats empty strings as null for some data types such as `IntegerType`.
   * - spark.sql.legacy.createEmptyCollectionUsingStringType
     - 3.0.0
     - false
     - When set to true, Spark returns an empty collection with `StringType` as element type if the `array`/`map` function is called without any parameters. Otherwise, Spark returns an empty collection with `NullType` as element type.
   * - spark.sql.legacy.allowUntypedScalaUDF
     - 3.0.0
     - false
     - When set to true, user is allowed to use org.apache.spark.sql.functions.udf(f: AnyRef, dataType: DataType). Otherwise, an exception will be thrown at runtime.
   * - spark.sql.legacy.dataset.nameNonStructGroupingKeyAsValue
     - 3.0.0
     - false
     - When set to true, the key attribute resulted from running `Dataset.groupByKey` for non-struct key type, will be named as `value`, following the behavior of Spark version 2.4 and earlier.
   * - spark.sql.legacy.setCommandRejectsSparkCoreConfs
     - 3.0.0
     - true
     - If it is set to true, SET command will fail when the key is registered as a SparkConf entry.
   * - spark.sql.legacy.typeCoercion.datetimeToString.enabled
     - 3.0.0
     - false
     - If it is set to true, date/timestamp will cast to string in binary comparisons with String when spark.sql.ansi.enabled is false.
   * - spark.sql.legacy.doLooseUpcast
     - 3.0.0
     - false
     - When true, the upcast will be loose and allows string to atomic types.
   * - spark.sql.legacy.ctePrecedencePolicy
     - 3.0.0
     - CORRECTED
     - When LEGACY, outer CTE definitions takes precedence over inner definitions. If set to EXCEPTION, AnalysisException is thrown while name conflict is detected in nested CTE.The default is CORRECTED, inner CTE definitions take precedence. This config will be removed in future versions and CORRECTED will be the only behavior.
   * - spark.sql.legacy.timeParserPolicy
     - 3.0.0
     - CORRECTED
     - When LEGACY, java.text.SimpleDateFormat is used for formatting and parsing dates/timestamps in a locale-sensitive manner, which is the approach before Spark 3.0. When set to CORRECTED, classes from java.time.* packages are used for the same purpose. When set to EXCEPTION, RuntimeException is thrown when we will get different results. The default is CORRECTED.
   * - spark.sql.legacy.followThreeValuedLogicInArrayExists
     - 3.0.0
     - true
     - When true, the ArrayExists will follow the three-valued boolean logic.
   * - spark.sql.legacy.fromDayTimeString.enabled
     - 3.0.0
     - false
     - When true, the `from` bound is not taken into account in conversion of a day-time string to an interval, and the `to` bound is used to skip all interval units out of the specified range. If it is set to `false`, `ParseException` is thrown if the input does not match to the pattern defined by `from` and `to`.
   * - spark.sql.legacy.notReserveProperties
     - 3.0.0
     - false
     - When true, all database and table properties are not reserved and available for create/alter syntaxes. But please be aware that the reserved properties will be silently removed.
   * - spark.sql.legacy.addSingleFileInAddFile
     - 3.0.0
     - false
     - When true, only a single file can be added using ADD FILE. If false, then users can add directory by passing directory path to ADD FILE.
   * - spark.sql.legacy.allowHashOnMapType
     - 3.0.0
     - false
     - When set to true, hash expressions can be applied on elements of MapType. Otherwise, an analysis exception will be thrown.
   * - spark.sql.legacy.parseNullPartitionSpecAsStringLiteral
     - 3.0.2
     - false
     - If it is set to true, `PARTITION(col=null)` is parsed as a string literal of its text representation, e.g., string 'null', when the partition column is string type. Otherwise, it is always parsed as a null literal in the partition spec.
   * - spark.sql.legacy.keepCommandOutputSchema
     - 3.0.2
     - false
     - When true, Spark will keep the output schema of commands such as SHOW DATABASES unchanged.
   * - spark.sql.legacy.useCurrentConfigsForView
     - 3.1.0
     - false
     - When true, SQL Configs of the current active SparkSession instead of the captured ones will be applied during the parsing and analysis phases of the view resolution.
   * - spark.sql.legacy.storeAnalyzedPlanForView
     - 3.1.0
     - false
     - When true, analyzed plan instead of SQL text will be stored when creating temporary view
   * - spark.sql.legacy.statisticalAggregate
     - 3.1.0
     - false
     - When set to true, statistical aggregate function returns Double.NaN if divide by zero occurred during expression evaluation, otherwise, it returns null. Before version 3.1.0, it returns NaN in divideByZero case by default.
   * - spark.sql.legacy.integerGroupingId
     - 3.1.0
     - false
     - When true, grouping_id() returns int values instead of long values.
   * - spark.sql.legacy.castComplexTypesToString.enabled
     - 3.1.0
     - false
     - When true, maps and structs are wrapped by [] in casting to strings, and NULL elements of structs/maps/arrays will be omitted while converting to strings. Otherwise, if this is false, which is the default, maps and structs are wrapped by {}, and NULL elements will be converted to "null".
   * - spark.sql.legacy.pathOptionBehavior.enabled
     - 3.1.0
     - false
     - When true, "path" option is overwritten if one path parameter is passed to DataFrameReader.load(), DataFrameWriter.save(), DataStreamReader.load(), or DataStreamWriter.start(). Also, "path" option is added to the overall paths if multiple path parameters are passed to DataFrameReader.load()
   * - spark.sql.legacy.extraOptionsBehavior.enabled
     - 3.1.0
     - false
     - When true, the extra options will be ignored for DataFrameReader.table(). If set it to false, which is the default, Spark will check if the extra options have the same key, but the value is different with the table serde properties. If the check passes, the extra options will be merged with the serde properties as the scan options. Otherwise, an exception will be thrown.
   * - spark.sql.legacy.createHiveTableByDefault
     - 3.1.0
     - false
     - When set to true, CREATE TABLE syntax without USING or STORED AS will use Hive instead of the value of spark.sql.sources.default as the table provider.
   * - spark.sql.legacy.charVarcharAsString
     - 3.1.0
     - false
     - When true, Spark treats CHAR/VARCHAR type the same as STRING type, which is the behavior of Spark 3.0 and earlier. This means no length check for CHAR/VARCHAR type and no padding for CHAR type when writing data to the table.
   * - spark.sql.legacy.allowParameterlessCount
     - 3.1.1
     - false
     - When true, the SQL function 'count' is allowed to take no parameters.
   * - spark.sql.legacy.allowStarWithSingleTableIdentifierInCount
     - 3.2
     - false
     - When true, the SQL function 'count' is allowed to take single 'tblName.*' as parameter
   * - spark.sql.legacy.allowNonEmptyLocationInCTAS
     - 3.2.0
     - false
     - When false, CTAS with LOCATION throws an analysis exception if the location is not empty.
   * - spark.sql.legacy.allowAutoGeneratedAliasForView
     - 3.2.0
     - false
     - When true, it's allowed to use a input query without explicit alias when creating a permanent view.
   * - spark.sql.legacy.interval.enabled
     - 3.2.0
     - false
     - When set to true, Spark SQL uses the mixed legacy interval type `CalendarIntervalType` instead of the ANSI compliant interval types `YearMonthIntervalType` and `DayTimeIntervalType`. For instance, the date subtraction expression returns `CalendarIntervalType` when the SQL config is set to `true` otherwise an ANSI interval.
   * - spark.sql.legacy.allowNullComparisonResultInArraySort
     - 3.2.2
     - false
     - When set to false, `array_sort` function throws an error if the comparator function returns null. If set to true, it restores the legacy behavior that handles null as zero (equal).
   * - spark.sql.legacy.groupingIdWithAppendedUserGroupBy
     - 3.2.3
     - false
     - When true, grouping_id() returns values based on grouping set columns plus user-given group-by expressions order like Spark 3.2.0, 3.2.1, 3.2.2, and 3.3.0.
   * - spark.sql.legacy.parquet.nanosAsLong
     - 3.2.4
     - false
     - When true, the Parquet's nanos precision timestamps are converted to SQL long values.
   * - spark.sql.legacy.allowZeroIndexInFormatString
     - 3.3
     - false
     - When false, the `strfmt` in `format_string(strfmt, obj, ...)` and `printf(strfmt, obj, ...)` will no longer support to use "0$" to specify the first argument, the first argument should always reference by "1$" when use argument index to indicating the position of the argument in the argument list. This config will be removed in the future releases.
   * - spark.sql.legacy.respectNullabilityInTextDatasetConversion
     - 3.3.0
     - false
     - When true, the nullability in the user-specified schema for `DataFrameReader.schema(schema).json(jsonDataset)` and `DataFrameReader.schema(schema).csv(csvDataset)` is respected. Otherwise, they are turned to a nullable schema forcibly.
   * - spark.sql.legacy.useV1Command
     - 3.3.0
     - false
     - When true, Spark will use legacy V1 SQL commands.
   * - spark.sql.legacy.histogramNumericPropagateInputType
     - 3.3.0
     - true
     - The histogram_numeric function computes a histogram on numeric 'expr' using nb bins. The return value is an array of (x,y) pairs representing the centers of the histogram's bins. If this config is set to true, the output type of the 'x' field in the return value is propagated from the input value consumed in the aggregate function. Otherwise, 'x' always has double type.
   * - spark.sql.legacy.lpadRpadAlwaysReturnString
     - 3.3.0
     - false
     - When set to false, when the first argument and the optional padding pattern is a byte sequence, the result is a BINARY value. The default padding pattern in this case is the zero byte. When set to true, it restores the legacy behavior of always returning string types even for binary inputs.
   * - spark.sql.legacy.nullValueWrittenAsQuotedEmptyStringCsv
     - 3.3.0
     - false
     - When set to false, nulls are written as unquoted empty strings in CSV data source. If set to true, it restores the legacy behavior that nulls were written as quoted empty strings, `""`.
   * - spark.sql.legacy.percentileDiscCalculation
     - 3.3.4
     - false
     - If true, the old bogus percentile_disc calculation is used. The old calculation incorrectly mapped the requested percentile to the sorted range of values in some cases and so returned incorrect results. Also, the new implementation is faster as it doesn't contain the interpolation logic that the old percentile_cont based one did.
   * - spark.sql.legacy.allowTempViewCreationWithMultipleNameparts
     - 3.4.0
     - false
     - When true, temp view creation Dataset APIs will allow the view creation even if the view name is multiple name parts. The extra name parts will be dropped during the view creation
   * - spark.sql.legacy.allowEmptySchemaWrite
     - 3.4.0
     - false
     - When this option is set to true, validation of empty or empty nested schemas that occurs when writing into a FileFormat based data source does not happen.
   * - spark.sql.legacy.skipTypeValidationOnAlterPartition
     - 3.4.0
     - false
     - When true, skip validation for partition spec in ALTER PARTITION. E.g., `ALTER TABLE .. ADD PARTITION(p='a')` would work even the partition type is int. When false, the behavior follows spark.sql.storeAssignmentPolicy
   * - spark.sql.legacy.keepPartitionSpecAsStringLiteral
     - 3.4.0
     - false
     - If it is set to true, `PARTITION(col=05)` is parsed as a string literal of its text representation, e.g., string '05', when the partition column is string type. Otherwise, it is always parsed as a numeric literal in the partition spec.
   * - spark.sql.legacy.csv.enableDateTimeParsingFallback
     - 3.4.0
     - <undefined>
     - When true, enable legacy date/time parsing fallback in CSV
   * - spark.sql.legacy.json.enableDateTimeParsingFallback
     - 3.4.0
     - <undefined>
     - When true, enable legacy date/time parsing fallback in JSON
   * - spark.sql.legacy.emptyCurrentDBInCli
     - 3.4.0
     - false
     - When false, spark-sql CLI prints the current database in prompt.
   * - spark.sql.legacy.v1IdentifierNoCatalog
     - 3.4.0
     - false
     - When set to false, the v1 identifier will include 'spark_catalog' as the catalog name if database is defined. When set to true, it restores the legacy behavior that does not include catalog name.
   * - spark.sql.legacy.negativeIndexInArrayInsert
     - 3.4.2
     - false
     - When set to true, restores the legacy behavior of `array_insert` for negative indexes - 0-based: the function inserts new element before the last one for the index -1. For example, `array_insert(['a', 'b'], -1, 'x')` returns `['a', 'x', 'b']`. When set to false, the -1 index points out to the last element, and the given example produces `['a', 'b', 'x']`.
   * - spark.sql.legacy.inSubqueryNullability
     - 3.5.0
     - false
     - When set to false, IN subquery nullability is correctly calculated based on both the left and right sides of the IN. When set to true, restores the legacy behavior that does not check the right side's nullability.
   * - spark.sql.legacy.nullInEmptyListBehavior
     - 3.5.0
     - <undefined>
     - When set to true, restores the legacy incorrect behavior of IN expressions for NULL values IN an empty list (including IN subqueries and literal IN lists): `null IN (empty list)` should evaluate to false, but sometimes (not always) incorrectly evaluates to null in the legacy behavior.
   * - spark.sql.legacy.avro.allowIncompatibleSchema
     - 3.5.1
     - false
     - When set to false, if types in Avro are encoded in the same format, but the type in the Avro schema explicitly says that the data types are different, reject reading the data type in the format to avoid returning incorrect results. When set to true, it restores the legacy behavior of allow reading the data in the format, which may return incorrect results.
   * - spark.sql.legacy.viewSchemaBindingMode
     - 4.0.0
     - true
     - Set to false to disable the WITH SCHEMA clause for view DDL and suppress the line in DESCRIBE EXTENDED and SHOW CREATE TABLE.
   * - spark.sql.legacy.viewSchemaCompensation
     - 4.0.0
     - true
     - Set to false to revert default view schema binding mode from WITH SCHEMA COMPENSATION to WITH SCHEMA BINDING.
   * - spark.sql.legacy.disableMapKeyNormalization
     - 4.0.0
     - false
     - Disables key normalization when creating a map with `ArrayBasedMapBuilder`. When set to `true` it will prevent key normalization when building a map, which will allow for values such as `-0.0` and `0.0` to be present as distinct keys.
   * - spark.sql.legacy.inlineCTEInCommands
     - 4.0.0
     - false
     - If true, always inline the CTE relations for the queries in commands. This is the legacy behavior which may produce incorrect results because Spark may evaluate a CTE relation more than once, even if it's nondeterministic.
   * - spark.sql.legacy.mssqlserver.datetimeoffsetMapping.enabled
     - 4.0.0
     - false
     - When true, DATETIMEOFFSET is mapped to StringType; otherwise, it is mapped to TimestampType.
   * - spark.sql.legacy.mysql.bitArrayMapping.enabled
     - 4.0.0
     - false
     - When true, use LongType to represent MySQL BIT(n>1); otherwise, use BinaryType.
   * - spark.sql.legacy.mysql.timestampNTZMapping.enabled
     - 4.0.0
     - false
     - When true, TimestampNTZType and MySQL TIMESTAMP can be converted bidirectionally. For reading, MySQL TIMESTAMP is converted to TimestampNTZType when JDBC read option preferTimestampNTZ is true. For writing, TimestampNTZType is converted to MySQL TIMESTAMP; otherwise, DATETIME
   * - spark.sql.legacy.oracle.timestampMapping.enabled
     - 4.0.0
     - false
     - When true, TimestampType maps to TIMESTAMP in Oracle; otherwise, TIMESTAMP WITH LOCAL TIME ZONE.
   * - spark.sql.legacy.db2.numericMapping.enabled
     - 4.0.0
     - false
     - When true, SMALLINT maps to IntegerType in DB2; otherwise, ShortType
   * - spark.sql.legacy.db2.booleanMapping.enabled
     - 4.0.0
     - false
     - When true, BooleanType maps to CHAR(1) in DB2; otherwise, BOOLEAN
   * - spark.sql.legacy.postgres.datetimeMapping.enabled
     - 4.0.0
     - false
     - When true, TimestampType maps to TIMESTAMP WITHOUT TIME ZONE in PostgreSQL for writing; otherwise, TIMESTAMP WITH TIME ZONE. When true, TIMESTAMP WITH TIME ZONE can be converted to TimestampNTZType when JDBC read option preferTimestampNTZ is true; otherwise, converted to TimestampType regardless of preferTimestampNTZ.
   * - spark.sql.legacy.raiseErrorWithoutErrorClass
     - 4.0.0
     - false
     - When set to true, restores the legacy behavior of `raise_error` and `assert_true` to not return the `[USER_RAISED_EXCEPTION]` prefix.For example, `raise_error('error!')` returns `error!` instead of `[USER_RAISED_EXCEPTION] Error!`.
   * - spark.sql.legacy.scalarSubqueryCountBugBehavior
     - 4.0.0
     - false
     - When set to true, restores legacy behavior of potential incorrect count bug handling for scalar subqueries.
   * - spark.sql.legacy.decimal.retainFractionDigitsOnTruncate
     - 4.0.0
     - false
     - When set to true, we will try to retain the fraction digits first rather than integral digits as prior Spark 4.0, when getting a least common type between decimal types, and the result decimal precision exceeds the max precision.
   * - spark.sql.legacy.javaCharsets
     - 4.0.0
     - false
     - When set to true, the functions like `encode()` can use charsets from JDK while encoding or decoding string values. If it is false, such functions support only one of the charsets: 'US-ASCII', 'ISO-8859-1', 'UTF-8', 'UTF-16BE', 'UTF-16LE', 'UTF-16'.
   * - spark.sql.legacy.earlyEvalCurrentTime
     - 4.0.0
     - false
     - When set to true, evaluation and constant folding will happen for now() and current_timestamp() expressions before finish analysis phase. This flag will allow a bit more liberal syntax but it will sacrifice correctness - Results of now() and current_timestamp() can be different for different operations in a single query.
   * - spark.sql.legacy.bangEqualsNot
     - 4.0.0
     - false
     - When set to true, '!' is a lexical equivalent for 'NOT'. That is '!' can be used outside of the documented prefix usage in a logical expression.Examples are: `expr ! IN (1, 2)` and `expr ! BETWEEN 1 AND 2`, but also `IF ! EXISTS`.

InMemoryTableScanStatistics(1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: InMemoryTableScanStatistics
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.inMemoryTableScanStatistics.enable
     - 3.0.0
     - false
     - When true, enable in-memory table scan accumulators.

CartesianProductExec(2)
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: CartesianProductExec
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.cartesianProductExec.buffer.spill.threshold
     - 2.2.0
     - 2147483647
     - Threshold for number of rows to be spilled by cartesian product operator
   * - spark.sql.cartesianProductExec.buffer.in.memory.threshold
     - 2.2.1
     - 4096
     - Threshold for number of rows guaranteed to be held in memory by the cartesian product operator

Analyzer(4)
~~~~~~~~~~~

.. list-table:: Analyzer
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.analyzer.maxIterations
     - 3.0.0
     - 100
     - The max number of iterations the analyzer runs.
   * - spark.sql.analyzer.failAmbiguousSelfJoin
     - 3.0.0
     - true
     - When true, fail the Dataset query if it contains ambiguous self-join.
   * - spark.sql.analyzer.canonicalization.multiCommutativeOpMemoryOptThreshold
     - 3.4.0
     - 3
     - The minimum number of operands in a commutative expression tree to invoke the MultiCommutativeOp memory optimization during canonicalization.
   * - spark.sql.analyzer.allowSubqueryExpressionsInLambdasOrHigherOrderFunctions
     - 4.0.0
     - false
     - When set to false, the analyzer will throw an error if a subquery expression appears in a lambda function or higher-order function. When set to true, it restores the legacy behavior of allowing subquery eexpressions in lambda functions or higher-order functions.

TruncateTable(1)
~~~~~~~~~~~~~~~~

.. list-table:: TruncateTable
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.truncateTable.ignorePermissionAcl.enabled
     - 2.4.6
     - false
     - When set to true, TRUNCATE TABLE command will not try to set back original permission and ACLs when re-creating the table/partition paths.

MaxConcurrentOutputFileWriters(1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: MaxConcurrentOutputFileWriters
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.maxConcurrentOutputFileWriters
     - 3.2.0
     - 0
     - Maximum number of output file writers to use concurrently. If number of writers needed reaches this limit, task will sort rest of output then writing them.

CrossJoin(1)
~~~~~~~~~~~~

.. list-table:: CrossJoin
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.crossJoin.enabled
     - 2.0.0
     - true
     - When false, we will throw an error if a query contains a cartesian product without explicit CROSS JOIN syntax.

Streaming(39)
~~~~~~~~~~~~~

.. list-table:: Streaming
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.streaming.stateStore.numStateStoreMaintenanceThreads
     - 
     - 3
     - Number of threads in the thread pool that perform clean up and snapshotting tasks for stateful streaming queries. The default value is the number of cores * 0.25 so that this thread pool doesn't take too many resources away from the query and affect performance.
   * - spark.sql.streaming.metadataCache.enabled
     - 
     - true
     - Whether the streaming HDFSMetadataLog caches the metadata of the latest two batches.
   * - spark.sql.streaming.triggerAvailableNowWrapper.enabled
     - 
     - false
     - Whether to use the wrapper implementation of Trigger.AvailableNow if the source does not support Trigger.AvailableNow. Enabling this allows the benefits of Trigger.AvailableNow with sources which don't support it, but some sources may show unexpected behavior including duplication, data loss, etc. So use with extreme care! The ideal direction is to persuade developers of source(s) to support Trigger.AvailableNow.
   * - spark.sql.streaming.stateStore.minDeltasForSnapshot
     - 2.0.0
     - 10
     - Minimum number of state store delta files that needs to be generated before they consolidated into snapshots.
   * - spark.sql.streaming.stateStore.maintenanceInterval
     - 2.0.0
     - 60000ms
     - The interval in milliseconds between triggering maintenance tasks in StateStore. The maintenance task executes background maintenance task in all the loaded store providers if they are still the active instances according to the coordinator. If not, inactive instances of store providers will be closed.
   * - spark.sql.streaming.unsupportedOperationCheck
     - 2.0.0
     - true
     - When true, the logical plan for streaming query will be checked for unsupported operations.
   * - spark.sql.streaming.fileSink.log.deletion
     - 2.0.0
     - true
     - Whether to delete the expired log files in file stream sink.
   * - spark.sql.streaming.fileSink.log.compactInterval
     - 2.0.0
     - 10
     - Number of log files after which all the previous files are compacted into the next log file.
   * - spark.sql.streaming.fileSink.log.cleanupDelay
     - 2.0.0
     - 600000ms
     - How long that a file is guaranteed to be visible for all readers.
   * - spark.sql.streaming.schemaInference
     - 2.0.0
     - false
     - Whether file-based streaming sources will infer its own schema
   * - spark.sql.streaming.pollingDelay
     - 2.0.0
     - 10ms
     - How long to delay polling new data when no data is available
   * - spark.sql.streaming.fileSource.log.deletion
     - 2.0.1
     - true
     - Whether to delete the expired log files in file stream source.
   * - spark.sql.streaming.fileSource.log.compactInterval
     - 2.0.1
     - 10
     - Number of log files after which all the previous files are compacted into the next log file.
   * - spark.sql.streaming.fileSource.log.cleanupDelay
     - 2.0.1
     - 600000ms
     - How long in milliseconds a file is guaranteed to be visible for all readers.
   * - spark.sql.streaming.commitProtocolClass
     - 2.1.0
     - org.apache.spark.sql.execution.streaming.ManifestFileCommitProtocol
     - 
   * - spark.sql.streaming.minBatchesToRetain
     - 2.1.1
     - 100
     - The minimum number of batches that must be retained and made recoverable.
   * - spark.sql.streaming.noDataProgressEventInterval
     - 2.1.1
     - 10000ms
     - How long to wait before providing query idle event when there is no data
   * - spark.sql.streaming.stateStore.providerClass
     - 2.3.0
     - org.apache.spark.sql.execution.streaming.state.HDFSBackedStateStoreProvider
     - The class used to manage state data in stateful streaming queries. This class must be a subclass of StateStoreProvider, and must have a zero-arg constructor. Note: For structured streaming, this configuration cannot be changed between query restarts from the same checkpoint location.
   * - spark.sql.streaming.continuous.executorQueueSize
     - 2.3.0
     - 1024
     - The size (measured in number of rows) of the queue used in continuous execution to buffer the results of a ContinuousDataReader.
   * - spark.sql.streaming.continuous.executorPollIntervalMs
     - 2.3.0
     - 100ms
     - The interval at which continuous execution readers will poll to check whether the epoch has advanced on the driver.
   * - spark.sql.streaming.flatMapGroupsWithState.stateFormatVersion
     - 2.4.0
     - 2
     - State format version used by flatMapGroupsWithState operation in a streaming query
   * - spark.sql.streaming.maxBatchesToRetainInMemory
     - 2.4.0
     - 2
     - The maximum number of batches which will be retained in memory to avoid loading from files. The value adjusts a trade-off between memory usage vs cache miss: '2' covers both success and direct failure cases, '1' covers only success case, and '0' covers extreme case - disable cache to maximize memory size of executors.
   * - spark.sql.streaming.aggregation.stateFormatVersion
     - 2.4.0
     - 2
     - State format version used by streaming aggregation operations in a streaming query. State between versions are tend to be incompatible, so state format version shouldn't be modified after running.
   * - spark.sql.streaming.disabledV2MicroBatchReaders
     - 2.4.0
     - 
     - A comma-separated list of fully qualified data source register class names for which MicroBatchReadSupport is disabled. Reads from these sources will fall back to the V1 Sources.
   * - spark.sql.streaming.join.stateFormatVersion
     - 3.0.0
     - 2
     - State format version used by streaming join operations in a streaming query. State between versions are tend to be incompatible, so state format version shouldn't be modified after running.
   * - spark.sql.streaming.fileSource.schema.forceNullable
     - 3.0.0
     - true
     - When true, force the schema of streaming file source to be nullable (including all the fields). Otherwise, the schema might not be compatible with actual data, which leads to corruptions.
   * - spark.sql.streaming.checkpoint.escapedPathCheck.enabled
     - 3.0.0
     - true
     - Whether to detect a streaming query may pick up an incorrect checkpoint path due to SPARK-26824.
   * - spark.sql.streaming.stateStore.formatValidation.enabled
     - 3.1.0
     - true
     - When true, check if the data from state store is valid or not when running streaming queries. This can happen if the state store format has been changed. Note, the feature is only effective in the build-in HDFS state store provider now.
   * - spark.sql.streaming.stateStore.compression.codec
     - 3.1.0
     - lz4
     - The codec used to compress delta and snapshot files generated by StateStore. By default, Spark provides four codecs: lz4, lzf, snappy, and zstd. You can also use fully qualified class names to specify the codec. Default codec is lz4.
   * - spark.sql.streaming.kafka.useDeprecatedOffsetFetching
     - 3.1.0
     - false
     - When true, the deprecated Consumer based offset fetching used which could cause infinite wait in Spark queries. Such cases query restart is the only workaround. For further details please see Offset Fetching chapter of Structured Streaming Kafka Integration Guide.
   * - spark.sql.streaming.statefulOperator.checkCorrectness.enabled
     - 3.1.0
     - true
     - When true, the stateful operators for streaming query will be checked for possible correctness issue due to global watermark. The correctness issue comes from queries containing stateful operation which can emit rows older than the current watermark plus allowed late record delay, which are "late rows" in downstream stateful operations and these rows can be discarded. Please refer the programming guide doc for more details. Once the issue is detected, Spark will throw analysis exception. When this config is disabled, Spark will just print warning message for users. Prior to Spark 3.1.0, the behavior is disabling this config.
   * - spark.sql.streaming.stateStore.rocksdb.formatVersion
     - 3.2.0
     - 5
     - Set the RocksDB format version. This will be stored in the checkpoint when starting a streaming query. The checkpoint will use this RocksDB format version in the entire lifetime of the query.
   * - spark.sql.streaming.sessionWindow.stateFormatVersion
     - 3.2.0
     - 1
     - State format version used by streaming session window in a streaming query. State between versions are tend to be incompatible, so state format version shouldn't be modified after running.
   * - spark.sql.streaming.fileStreamSink.ignoreMetadata
     - 3.2.0
     - false
     - If this is enabled, when Spark reads from the results of a streaming query written by `FileStreamSink`, Spark will ignore the metadata log and treat it as normal path to read, e.g. listing files using HDFS APIs.
   * - spark.sql.streaming.statefulOperator.useStrictDistribution
     - 3.3.0
     - true
     - The purpose of this config is only compatibility; DO NOT MANUALLY CHANGE THIS!!! When true, the stateful operator for streaming query will use StatefulOpClusteredDistribution which guarantees stable state partitioning as long as the operator provides consistent grouping keys across the lifetime of query. When false, the stateful operator for streaming query will use ClusteredDistribution which is not sufficient to guarantee stable state partitioning despite the operator provides consistent grouping keys across the lifetime of query. This config will be set to true for new streaming queries to guarantee stable state partitioning, and set to false for existing streaming queries to not break queries which are restored from existing checkpoints. Please refer SPARK-38204 for details.
   * - spark.sql.streaming.stateStore.skipNullsForStreamStreamJoins.enabled
     - 3.3.0
     - false
     - When true, this config will skip null values in hash based stream-stream joins. The number of skipped null values will be shown as custom metric of stream join operator.
   * - spark.sql.streaming.checkpoint.renamedFileCheck.enabled
     - 3.4.0
     - false
     - When true, Spark will validate if renamed checkpoint file exists.
   * - spark.sql.streaming.statefulOperator.allowMultiple
     - 3.4.0
     - true
     - When true, multiple stateful operators are allowed to be present in a streaming pipeline. The support for multiple stateful operators introduces a minor (semantically correct) change in respect to late record filtering - late records are detected and filtered in respect to the watermark from the previous microbatch instead of the current one. This is a behavior change for Spark streaming pipelines and we allow users to revert to the previous behavior of late record filtering (late records are detected and filtered by comparing with the current microbatch watermark) by setting the flag value to false. In this mode, only a single stateful operator will be allowed in a streaming pipeline.
   * - spark.sql.streaming.asyncLogPurge.enabled
     - 3.4.0
     - true
     - When true, purging the offset log and commit log of old entries will be done asynchronously.

Join(1)
~~~~~~~

.. list-table:: Join
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.join.preferSortMergeJoin
     - 2.0.0
     - true
     - When true, prefer sort merge join over shuffled hash join. Sort merge join consumes less memory than shuffled hash join and it works efficiently when both join tables are large. On the other hand, shuffled hash join can improve performance (e.g., of full outer joins) when one of join tables is much smaller.

ObjectHashAggregate(1)
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: ObjectHashAggregate
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.objectHashAggregate.sortBased.fallbackThreshold
     - 2.2.0
     - 128
     - In the case of ObjectHashAggregateExec, when the size of the in-memory hash map grows too large, we will fall back to sort-based aggregation. This option sets a row count threshold for the size of the hash map.

StableDerivedColumnAlias(1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: StableDerivedColumnAlias
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.stableDerivedColumnAlias.enabled
     - 3.5.0
     - false
     - Enable deriving of stable column aliases from the lexer tree instead of parse tree and form them via pretty SQL print.

Statistics(4)
~~~~~~~~~~~~~

.. list-table:: Statistics
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.statistics.ndv.maxError
     - 2.1.1
     - 0.05
     - The maximum relative standard deviation allowed in HyperLogLog++ algorithm when generating column level statistics.
   * - spark.sql.statistics.histogram.numBins
     - 2.3.0
     - 254
     - The number of bins when generating histograms.
   * - spark.sql.statistics.percentile.accuracy
     - 2.3.0
     - 10000
     - Accuracy of percentile approximation when generating equi-height histograms. Larger value means better accuracy. The relative error can be deduced by 1.0 / PERCENTILE_ACCURACY.
   * - spark.sql.statistics.parallelFileListingInStatsComputation.enabled
     - 2.4.1
     - true
     - When true, SQL commands use parallel file listing, as opposed to single thread listing. This usually speeds up commands that need to list many directories.

Json(2)
~~~~~~~

.. list-table:: Json
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.json.enablePartialResults
     - 3.4.0
     - true
     - When set to true, enables partial results for structs, maps, and arrays in JSON when one or more fields do not match the schema
   * - spark.sql.json.enableExactStringParsing
     - 4.0.0
     - true
     - When set to true, string columns extracted from JSON objects will be extracted exactly as they appear in the input string, with no changes

WindowExec(2)
~~~~~~~~~~~~~

.. list-table:: WindowExec
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.windowExec.buffer.spill.threshold
     - 2.2.0
     - 2147483647
     - Threshold for number of rows to be spilled by window operator
   * - spark.sql.windowExec.buffer.in.memory.threshold
     - 2.2.1
     - 4096
     - Threshold for number of rows guaranteed to be held in memory by the window operator

SelfJoinAutoResolveAmbiguity(1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: SelfJoinAutoResolveAmbiguity
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.selfJoinAutoResolveAmbiguity
     - 1.4.0
     - true
     - 

RunSQLOnFiles(1)
~~~~~~~~~~~~~~~~

.. list-table:: RunSQLOnFiles
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.runSQLOnFiles
     - 1.6.0
     - true
     - When true, we could use `datasource`.`path` as table in SQL query.

Orc(1)
~~~~~~

.. list-table:: Orc
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.orc.impl
     - 2.3.0
     - native
     - When native, use the native version of ORC support instead of the ORC library in Hive. It is 'hive' by default prior to Spark 2.4.

LateralColumnAlias(1)
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: LateralColumnAlias
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.lateralColumnAlias.enableImplicitResolution
     - 3.4.0
     - true
     - Enable resolving implicit lateral column alias defined in the same SELECT list. For example, with this conf turned on, for query `SELECT 1 AS a, a + 1` the `a` in `a + 1` can be resolved as the previously defined `1 AS a`. But note that table column has higher resolution priority than the lateral column alias.

Parser(1)
~~~~~~~~~

.. list-table:: Parser
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.parser.escapedStringLiterals
     - 2.2.1
     - false
     - When true, string literals (including regex patterns) remain escaped in our SQL parser. The default is false since Spark 2.0. Setting it to true can restore the behavior prior to Spark 2.0.

Parquet(11)
~~~~~~~~~~~

.. list-table:: Parquet
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.parquet.output.committer.class
     - 1.5.0
     - org.apache.parquet.hadoop.ParquetOutputCommitter
     - The output committer class used by Parquet. The specified class needs to be a subclass of org.apache.hadoop.mapreduce.OutputCommitter. Typically, it's also a subclass of org.apache.parquet.hadoop.ParquetOutputCommitter. If it is not, then metadata summaries will never be created, irrespective of the value of parquet.summary.metadata.level
   * - spark.sql.parquet.filterPushdown.date
     - 2.4.0
     - true
     - If true, enables Parquet filter push-down optimization for Date. This configuration only has an effect when 'spark.sql.parquet.filterPushdown' is enabled.
   * - spark.sql.parquet.filterPushdown.timestamp
     - 2.4.0
     - true
     - If true, enables Parquet filter push-down optimization for Timestamp. This configuration only has an effect when 'spark.sql.parquet.filterPushdown' is enabled and Timestamp stored as TIMESTAMP_MICROS or TIMESTAMP_MILLIS type.
   * - spark.sql.parquet.filterPushdown.decimal
     - 2.4.0
     - true
     - If true, enables Parquet filter push-down optimization for Decimal. This configuration only has an effect when 'spark.sql.parquet.filterPushdown' is enabled.
   * - spark.sql.parquet.filterPushdown.string.startsWith
     - 2.4.0
     - true
     - If true, enables Parquet filter push-down optimization for string startsWith function. This configuration only has an effect when 'spark.sql.parquet.filterPushdown' is enabled.
   * - spark.sql.parquet.pushdown.inFilterThreshold
     - 2.4.0
     - 10
     - For IN predicate, Parquet filter will push-down a set of OR clauses if its number of values not exceeds this threshold. Otherwise, Parquet filter will push-down a value greater than or equal to its minimum value and less than or equal to its maximum value. By setting this value to 0 this feature can be disabled. This configuration only has an effect when 'spark.sql.parquet.filterPushdown' is enabled.
   * - spark.sql.parquet.datetimeRebaseModeInWrite
     - 3.0.0
     - CORRECTED
     - When LEGACY, Spark will rebase dates/timestamps from Proleptic Gregorian calendar to the legacy hybrid (Julian + Gregorian) calendar when writing Parquet files. When CORRECTED, Spark will not do rebase and write the dates/timestamps as it is. When EXCEPTION, which is the default, Spark will fail the writing if it sees ancient dates/timestamps that are ambiguous between the two calendars. This config influences on writes of the following parquet logical types: DATE, TIMESTAMP_MILLIS, TIMESTAMP_MICROS. The INT96 type has the separate config: spark.sql.parquet.int96RebaseModeInWrite.
   * - spark.sql.parquet.datetimeRebaseModeInRead
     - 3.0.0
     - CORRECTED
     - When LEGACY, Spark will rebase dates/timestamps from the legacy hybrid (Julian + Gregorian) calendar to Proleptic Gregorian calendar when reading Parquet files. When CORRECTED, Spark will not do rebase and read the dates/timestamps as it is. When EXCEPTION, which is the default, Spark will fail the reading if it sees ancient dates/timestamps that are ambiguous between the two calendars. This config is only effective if the writer info (like Spark, Hive) of the Parquet files is unknown. This config influences on reads of the following parquet logical types: DATE, TIMESTAMP_MILLIS, TIMESTAMP_MICROS. The INT96 type has the separate config: spark.sql.parquet.int96RebaseModeInRead.
   * - spark.sql.parquet.int96RebaseModeInWrite
     - 3.1.0
     - CORRECTED
     - When LEGACY, Spark will rebase INT96 timestamps from Proleptic Gregorian calendar to the legacy hybrid (Julian + Gregorian) calendar when writing Parquet files. When CORRECTED, Spark will not do rebase and write the timestamps as it is. When EXCEPTION, which is the default, Spark will fail the writing if it sees ancient timestamps that are ambiguous between the two calendars.
   * - spark.sql.parquet.int96RebaseModeInRead
     - 3.1.0
     - CORRECTED
     - When LEGACY, Spark will rebase INT96 timestamps from the legacy hybrid (Julian + Gregorian) calendar to Proleptic Gregorian calendar when reading Parquet files. When CORRECTED, Spark will not do rebase and read the timestamps as it is. When EXCEPTION, which is the default, Spark will fail the reading if it sees ancient timestamps that are ambiguous between the two calendars. This config is only effective if the writer info (like Spark, Hive) of the Parquet files is unknown.
   * - spark.sql.parquet.filterPushdown.stringPredicate
     - 3.4.0
     - <value of spark.sql.parquet.filterPushdown.string.startsWith>
     - If true, enables Parquet filter push-down optimization for string predicate such as startsWith/endsWith/contains function. This configuration only has an effect when 'spark.sql.parquet.filterPushdown' is enabled.

Csv(2)
~~~~~~

.. list-table:: Csv
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.csv.parser.columnPruning.enabled
     - 2.4.0
     - true
     - If it is set to true, column names of the requested schema are passed to CSV parser. Other column values can be ignored during parsing even if they are malformed.
   * - spark.sql.csv.parser.inputBufferSize
     - 3.0.3
     - <undefined>
     - If it is set, it configures the buffer size of CSV input during parsing. It is the same as inputBufferSize option in CSV which has a higher priority. Note that this is a workaround for the parsing library's regression, and this configuration is internal and supposed to be removed in the near future.

ScriptTransformation(1)
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: ScriptTransformation
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.scriptTransformation.exitTimeoutInSeconds
     - 3.0.0
     - 10000ms
     - Timeout for executor to wait for the termination of transformation script when EOF.

Codegen(20)
~~~~~~~~~~~

.. list-table:: Codegen
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.codegen.wholeStage
     - 2.0.0
     - true
     - When true, the whole stage (of multiple operators) will be compiled into single java method.
   * - spark.sql.codegen.maxFields
     - 2.0.0
     - 100
     - The maximum number of fields (including nested fields) that will be supported before deactivating whole-stage codegen.
   * - spark.sql.codegen.fallback
     - 2.0.0
     - true
     - When true, (whole stage) codegen could be temporary disabled for the part of query that fail to compile generated code
   * - spark.sql.codegen.logging.maxLines
     - 2.3.0
     - 1000
     - The maximum number of codegen lines to log when errors occur. Use -1 for unlimited.
   * - spark.sql.codegen.hugeMethodLimit
     - 2.3.0
     - 65535
     - The maximum bytecode size of a single compiled Java function generated by whole-stage codegen. When the compiled function exceeds this threshold, the whole-stage codegen is deactivated for this subtree of the current query plan. The default value is 65535, which is the largest bytecode size possible for a valid Java method. When running on HotSpot, it may be preferable to set the value to 8000 to match HotSpot's implementation.
   * - spark.sql.codegen.aggregate.map.twolevel.enabled
     - 2.3.0
     - true
     - Enable two-level aggregate hash map. When enabled, records will first be inserted/looked-up at a 1st-level, small, fast map, and then fallback to a 2nd-level, larger, slower map when 1st level is full or keys cannot be found. When disabled, records go directly to the 2nd level.
   * - spark.sql.codegen.useIdInClassName
     - 2.3.1
     - true
     - When true, embed the (whole-stage) codegen stage ID into the class name of the generated class as a suffix
   * - spark.sql.codegen.splitConsumeFuncByOperator
     - 2.3.1
     - true
     - When true, whole stage codegen would put the logic of consuming rows of each physical operator into individual methods, instead of a single big method. This can be used to avoid oversized function that can miss the opportunity of JIT optimization.
   * - spark.sql.codegen.factoryMode
     - 2.4.0
     - FALLBACK
     - This config determines the fallback behavior of several codegen generators during tests. `FALLBACK` means trying codegen first and then falling back to interpreted if any compile error happens. Disabling fallback if `CODEGEN_ONLY`. `NO_CODEGEN` skips codegen and goes interpreted path always. Note that this configuration is only for the internal usage, and NOT supposed to be set by end users.
   * - spark.sql.codegen.aggregate.fastHashMap.capacityBit
     - 2.4.0
     - 16
     - Capacity for the max number of rows to be held in memory by the fast hash aggregate product operator. The bit is not for actual value, but the actual numBuckets is determined by loadFactor (e.g: default bit value 16 , the actual numBuckets is ((1 << 16) / 0.5).
   * - spark.sql.codegen.methodSplitThreshold
     - 3.0.0
     - 1024
     - The threshold of source-code splitting in the codegen. When the number of characters in a single Java function (without comment) exceeds the threshold, the function will be automatically split to multiple smaller ones. We cannot know how many bytecode will be generated, so use the code length as metric. When running on HotSpot, a function's bytecode should not go beyond 8KB, otherwise it will not be JITted; it also should not be too small, otherwise there will be many function calls.
   * - spark.sql.codegen.aggregate.map.vectorized.enable
     - 3.0.0
     - false
     - Enable vectorized aggregate hash map. This is for testing/benchmarking only.
   * - spark.sql.codegen.aggregate.splitAggregateFunc.enabled
     - 3.0.0
     - true
     - When true, the code generator would split aggregate code into individual methods instead of a single big method. This can be used to avoid oversized function that can miss the opportunity of JIT optimization.
   * - spark.sql.codegen.aggregate.map.twolevel.partialOnly
     - 3.2.1
     - true
     - Enable two-level aggregate hash map for partial aggregate only, because final aggregate might get more distinct keys compared to partial aggregate. Overhead of looking up 1st-level map might dominate when having a lot of distinct keys.
   * - spark.sql.codegen.aggregate.sortAggregate.enabled
     - 3.3.0
     - true
     - When true, enable code-gen for sort aggregate.
   * - spark.sql.codegen.join.fullOuterShuffledHashJoin.enabled
     - 3.3.0
     - true
     - When true, enable code-gen for FULL OUTER shuffled hash join.
   * - spark.sql.codegen.join.fullOuterSortMergeJoin.enabled
     - 3.3.0
     - true
     - When true, enable code-gen for FULL OUTER sort merge join.
   * - spark.sql.codegen.join.existenceSortMergeJoin.enabled
     - 3.3.0
     - true
     - When true, enable code-gen for Existence sort merge join.
   * - spark.sql.codegen.join.buildSideOuterShuffledHashJoin.enabled
     - 3.5.0
     - true
     - When true, enable code-gen for an OUTER shuffled hash join where outer side is the build side.
   * - spark.sql.codegen.broadcastCleanedSourceThreshold
     - 4.0.0
     - -1
     - A threshold (in string length) to determine if we should make the generated code abroadcast variable in whole stage codegen. To disable this, set the threshold to < 0; otherwise if the size is above the threshold, it'll use broadcast variable. Note that maximum string length allowed in Java is Integer.MAX_VALUE, so anything above it would be meaningless. The default value is set to -1 (disabled by default).

AddPartitionInBatch(1)
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: AddPartitionInBatch
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.addPartitionInBatch.size
     - 3.0.0
     - 100
     - The number of partitions to be handled in one turn when use `AlterTableAddPartitionCommand` or `RepairTableCommand` to add partitions into table. The smaller batch size is, the less memory is required for the real handler, e.g. Hive Metastore.

InMemoryColumnarStorage(1)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: InMemoryColumnarStorage
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.inMemoryColumnarStorage.partitionPruning
     - 1.2.0
     - true
     - When true, enable partition pruning for in-memory columnar tables.

RetainGroupColumns(1)
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: RetainGroupColumns
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.retainGroupColumns
     - 1.4.0
     - true
     - 

Files(1)
~~~~~~~~

.. list-table:: Files
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.files.openCostInBytes
     - 2.0.0
     - 4MB
     - The estimated cost to open a file, measured by the number of bytes could be scanned in the same time. This is used when putting multiple files into a partition. It's better to over estimated, then the partitions with small files will be faster than partitions with bigger files (which is scheduled first). This configuration is effective only when using file-based sources such as Parquet, JSON and ORC.

CaseSensitive(1)
~~~~~~~~~~~~~~~~

.. list-table:: CaseSensitive
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.caseSensitive
     - 1.4.0
     - false
     - Whether the query analyzer should be case sensitive or not. Default to case insensitive. It is highly discouraged to turn on case sensitive mode.

Exchange(1)
~~~~~~~~~~~

.. list-table:: Exchange
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.exchange.reuse
     - 2.0.0
     - true
     - When true, the planner will try to find out duplicated exchanges and re-use them.

Avro(2)
~~~~~~~

.. list-table:: Avro
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.avro.datetimeRebaseModeInWrite
     - 3.0.0
     - CORRECTED
     - When LEGACY, Spark will rebase dates/timestamps from Proleptic Gregorian calendar to the legacy hybrid (Julian + Gregorian) calendar when writing Avro files. When CORRECTED, Spark will not do rebase and write the dates/timestamps as it is. When EXCEPTION, which is the default, Spark will fail the writing if it sees ancient dates/timestamps that are ambiguous between the two calendars.
   * - spark.sql.avro.datetimeRebaseModeInRead
     - 3.0.0
     - CORRECTED
     - When LEGACY, Spark will rebase dates/timestamps from the legacy hybrid (Julian + Gregorian) calendar to Proleptic Gregorian calendar when reading Avro files. When CORRECTED, Spark will not do rebase and read the dates/timestamps as it is. When EXCEPTION, which is the default, Spark will fail the reading if it sees ancient dates/timestamps that are ambiguous between the two calendars. This config is only effective if the writer info (like Spark, Hive) of the Avro files is unknown.

SortMergeJoinExec(2)
~~~~~~~~~~~~~~~~~~~~

.. list-table:: SortMergeJoinExec
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.sortMergeJoinExec.buffer.spill.threshold
     - 2.2.0
     - 2147483647
     - Threshold for number of rows to be spilled by sort merge join operator
   * - spark.sql.sortMergeJoinExec.buffer.in.memory.threshold
     - 2.2.1
     - 2147483632
     - Threshold for number of rows guaranteed to be held in memory by the sort merge join operator

Pyspark(2)
~~~~~~~~~~

.. list-table:: Pyspark
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.pyspark.legacy.inferArrayTypeFromFirstElement.enabled
     - 3.4.0
     - false
     - PySpark's SparkSession.createDataFrame infers the element type of an array from all values in the array by default. If this config is set to true, it restores the legacy behavior of only inferring the type from the first array element.
   * - spark.sql.pyspark.legacy.inferMapTypeFromFirstPair.enabled
     - 4.0.0
     - false
     - PySpark's SparkSession.createDataFrame infers the key/value types of a map from all paris in the map by default. If this config is set to true, it restores the legacy behavior of only inferring the type from the first non-null pair.

DecimalOperations(1)
~~~~~~~~~~~~~~~~~~~~

.. list-table:: DecimalOperations
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.decimalOperations.allowPrecisionLoss
     - 2.3.1
     - true
     - When true (default), establishing the result type of an arithmetic operation happens according to Hive behavior and SQL ANSI 2011 specification, i.e. rounding the decimal part of the result if an exact representation is not possible. Otherwise, NULL is returned in those cases, as previously.

Hive(6)
~~~~~~~

.. list-table:: Hive
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.hive.convertCTAS
     - 2.0.0
     - false
     - When true, a table created by a Hive CTAS statement (no USING clause) without specifying any storage property will be converted to a data source table, using the data source set by spark.sql.sources.default.
   * - spark.sql.hive.gatherFastStats
     - 2.0.1
     - true
     - When true, fast stats (number of files and total size of all files) will be gathered in parallel while repairing table partitions to avoid the sequential listing in Hive metastore.
   * - spark.sql.hive.caseSensitiveInferenceMode
     - 2.1.1
     - NEVER_INFER
     - Sets the action to take when a case-sensitive schema cannot be read from a Hive Serde table's properties when reading the table with Spark native data sources. Valid options include INFER_AND_SAVE (infer the case-sensitive schema from the underlying data files and write it back to the table properties), INFER_ONLY (infer the schema but don't attempt to write it to the table properties) and NEVER_INFER (the default mode-- fallback to using the case-insensitive metastore schema instead of inferring).
   * - spark.sql.hive.advancedPartitionPredicatePushdown.enabled
     - 2.3.0
     - true
     - When true, advanced partition predicate pushdown into Hive metastore is enabled.
   * - spark.sql.hive.metastorePartitionPruningInSetThreshold
     - 3.1.0
     - 1000
     - The threshold of set size for InSet predicate when pruning partitions through Hive Metastore. When the set size exceeds the threshold, we rewrite the InSet predicate to be greater than or equal to the minimum value in set and less than or equal to the maximum value in set. Larger values may cause Hive Metastore stack overflow. But for InSet inside Not with values exceeding the threshold, we won't push it to Hive Metastore.
   * - spark.sql.hive.tablePropertyLengthThreshold
     - 3.2.0
     - <undefined>
     - The maximum length allowed in a single cell when storing Spark-specific information in Hive's metastore as table properties. Currently it covers 2 things: the schema's JSON string, the histogram of column statistics.

UseCommonExprIdForAlias(1)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: UseCommonExprIdForAlias
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.useCommonExprIdForAlias
     - 4.0.0
     - true
     - When true, use the common expression ID for the alias when rewriting With expressions. Otherwise, use the index of the common expression definition. When true this avoids duplicate alias names, but is helpful to set to false for testing to ensurethat alias names are consistent.

OptimizeNullAwareAntiJoin(1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: OptimizeNullAwareAntiJoin
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.optimizeNullAwareAntiJoin
     - 3.1.0
     - true
     - When true, NULL-aware anti join execution will be planed into BroadcastHashJoinExec with flag isNullAwareAntiJoin enabled, optimized from O(M*N) calculation into O(M) calculation using Hash lookup instead of Looping lookup.Only support for singleColumn NAAJ for now.

Adaptive(7)
~~~~~~~~~~~

.. list-table:: Adaptive
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.adaptive.shuffle.targetPostShuffleInputSize
     - 1.6.0
     - 64MB
     - (Deprecated since Spark 3.0)
   * - spark.sql.adaptive.forceApply
     - 3.0.0
     - false
     - Adaptive query execution is skipped when the query does not have exchanges or sub-queries. By setting this config to true (together with 'spark.sql.adaptive.enabled' set to true), Spark will force apply adaptive query execution for all supported queries.
   * - spark.sql.adaptive.logLevel
     - 3.0.0
     - debug
     - Configures the log level for adaptive execution logging of plan changes. The value can be 'trace', 'debug', 'info', 'warn', or 'error'. The default log level is 'debug'.
   * - spark.sql.adaptive.coalescePartitions.minPartitionNum
     - 3.0.0
     - <undefined>
     - (deprecated) The suggested (not guaranteed) minimum number of shuffle partitions after coalescing. If not set, the default value is the default parallelism of the Spark cluster. This configuration only has an effect when 'spark.sql.adaptive.enabled' and 'spark.sql.adaptive.coalescePartitions.enabled' are both true.
   * - spark.sql.adaptive.fetchShuffleBlocksInBatch
     - 3.0.0
     - true
     - Whether to fetch the contiguous shuffle blocks in batch. Instead of fetching blocks one by one, fetching contiguous shuffle blocks for the same map task in batch can reduce IO and improve performance. Note, multiple contiguous blocks exist in single fetch request only happen when 'spark.sql.adaptive.enabled' and 'spark.sql.adaptive.coalescePartitions.enabled' are both true. This feature also depends on a relocatable serializer, the concatenation support codec in use, the new version shuffle fetch protocol and io encryption is disabled.
   * - spark.sql.adaptive.nonEmptyPartitionRatioForBroadcastJoin
     - 3.0.0
     - 0.2
     - The relation with a non-empty partition ratio lower than this config will not be considered as the build side of a broadcast-hash join in adaptive execution regardless of its size.This configuration only has an effect when 'spark.sql.adaptive.enabled' is true.
   * - spark.sql.adaptive.applyFinalStageShuffleOptimizations
     - 3.4.2
     - true
     - Configures whether adaptive query execution (if enabled) should apply shuffle coalescing and local shuffle read optimization for the final query stage.

AlwaysInlineCommonExpr(1)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: AlwaysInlineCommonExpr
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.alwaysInlineCommonExpr
     - 4.0.0
     - false
     - When true, always inline common expressions instead of using the WITH expression. This may lead to duplicated expressions and the config should only be enabled if you hit bugs caused by the WITH expression.

Sort(1)
~~~~~~~

.. list-table:: Sort
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.sort.enableRadixSort
     - 2.0.0
     - true
     - When true, enable use of radix sort when possible. Radix sort is much faster but requires additional memory to be reserved up-front. The memory overhead may be significant when sorting very small rows (up to 50% more in this case).

RequireAllClusterKeysForCoPartition(1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: RequireAllClusterKeysForCoPartition
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.requireAllClusterKeysForCoPartition
     - 3.3.0
     - true
     - When true, the planner requires all the clustering keys as the hash partition keys of the children, to eliminate the shuffles for the operator that needs its children to be co-partitioned, such as JOIN node. This is to avoid data skews which can lead to significant performance regression if shuffles are eliminated.

Limit(2)
~~~~~~~~

.. list-table:: Limit
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.limit.scaleUpFactor
     - 2.1.1
     - 4
     - Minimal increase rate in number of partitions between attempts when executing a take on a query. Higher values lead to more partitions read. Lower values might lead to longer execution times as more jobs will be run
   * - spark.sql.limit.initialNumPartitions
     - 3.4.0
     - 1
     - Initial number of partitions to try when executing a take on a query. Higher values lead to more partitions read. Lower values might lead to longer execution times as morejobs will be run

Sources(9)
~~~~~~~~~~

.. list-table:: Sources
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.sources.outputCommitterClass
     - 1.4.0
     - <undefined>
     - 
   * - spark.sql.sources.commitProtocolClass
     - 2.1.1
     - org.apache.spark.sql.execution.datasources.SQLHadoopMapReduceCommitProtocol
     - 
   * - spark.sql.sources.parallelPartitionDiscovery.parallelism
     - 2.1.1
     - 10000
     - The number of parallelism to list a collection of path recursively, Set the number to prevent file listing from generating too many tasks.
   * - spark.sql.sources.fileCompressionFactor
     - 2.3.1
     - 1.0
     - When estimating the output data size of a table scan, multiply the file size with this factor as the estimated data size, in case the data is compressed in the file and lead to a heavily underestimated result.
   * - spark.sql.sources.ignoreDataLocality
     - 3.0.0
     - false
     - If true, Spark will not fetch the block locations for each file on listing files. This speeds up file listing, but the scheduler cannot schedule tasks to take advantage of data locality. It can be particularly useful if data is read from a remote cluster so the scheduler could never take advantage of locality anyway.
   * - spark.sql.sources.validatePartitionColumns
     - 3.0.0
     - true
     - When this option is set to true, partition column values will be validated with user-specified schema. If the validation fails, a runtime exception is thrown. When this option is set to false, the partition column value will be converted to null if it can not be casted to corresponding user-specified schema.
   * - spark.sql.sources.useV1SourceList
     - 3.0.0
     - avro,csv,json,kafka,orc,parquet,text
     - A comma-separated list of data source short names or fully qualified data source implementation class names for which Data Source V2 code path is disabled. These data sources will fallback to Data Source V1 code path.
   * - spark.sql.sources.binaryFile.maxLength
     - 3.0.0
     - 2147483647
     - The max length of a file that can be read by the binary file data source. Spark will fail fast and not attempt to read the file if its length exceeds this value. The theoretical max is Int.MaxValue, though VMs might implement a smaller max.
   * - spark.sql.sources.useListFilesFileSystemList
     - 4.0.0
     - s3a
     - A comma-separated list of file system schemes to use FileSystem.listFiles API for a single root path listing

DefaultColumn(3)
~~~~~~~~~~~~~~~~

.. list-table:: DefaultColumn
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.defaultColumn.enabled
     - 3.4.0
     - true
     - When true, allow CREATE TABLE, REPLACE TABLE, and ALTER COLUMN statements to set or update default values for specific columns. Following INSERT, MERGE, and UPDATE statements may then omit these values and their values will be injected automatically instead.
   * - spark.sql.defaultColumn.allowedProviders
     - 3.4.0
     - csv,json,orc,parquet
     - List of table providers wherein SQL commands are permitted to assign DEFAULT column values. Comma-separated list, whitespace ignored, case-insensitive. If an asterisk appears after any table provider in this list, any command may assign DEFAULT column except `ALTER TABLE ... ADD COLUMN`. Otherwise, if no asterisk appears, all commands are permitted. This is useful because in order for such `ALTER TABLE ... ADD COLUMN` commands to work, the target data source must include support for substituting in the provided values when the corresponding fields are not present in storage.
   * - spark.sql.defaultColumn.useNullsForMissingDefaultValues
     - 3.4.0
     - true
     - When true, and DEFAULT columns are enabled, allow INSERT INTO commands with user-specified lists of fewer columns than the target table to behave as if they had specified DEFAULT for all remaining columns instead, in order.

PlanChangeLog(3)
~~~~~~~~~~~~~~~~

.. list-table:: PlanChangeLog
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.planChangeLog.level
     - 3.1.0
     - trace
     - Configures the log level for logging the change from the original plan to the new plan after a rule or batch is applied. The value can be 'trace', 'debug', 'info', 'warn', or 'error'. The default log level is 'trace'.
   * - spark.sql.planChangeLog.rules
     - 3.1.0
     - <undefined>
     - Configures a list of rules for logging plan changes, in which the rules are specified by their rule names and separated by comma.
   * - spark.sql.planChangeLog.batches
     - 3.1.0
     - <undefined>
     - Configures a list of batches for logging plan changes, in which the batches are specified by their batch names and separated by comma.

SessionWindow(2)
~~~~~~~~~~~~~~~~

.. list-table:: SessionWindow
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.sessionWindow.buffer.in.memory.threshold
     - 3.2.0
     - 4096
     - Threshold for number of windows guaranteed to be held in memory by the session window operator. Note that the buffer is used only for the query Spark cannot apply aggregations on determining session window.
   * - spark.sql.sessionWindow.buffer.spill.threshold
     - 3.2.0
     - 2147483647
     - Threshold for number of rows to be spilled by window operator. Note that the buffer is used only for the query Spark cannot apply aggregations on determining session window.

ConstraintPropagation(1)
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: ConstraintPropagation
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.constraintPropagation.enabled
     - 2.2.0
     - true
     - When true, the query optimizer will infer and propagate data constraints in the query plan to optimize them. Constraint propagation can sometimes be computationally expensive for certain kinds of query plans (such as those with a large number of predicates and aliases) which might negatively impact overall runtime.

SubexpressionElimination(3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: SubexpressionElimination
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.subexpressionElimination.enabled
     - 1.6.0
     - true
     - When true, common subexpressions will be eliminated.
   * - spark.sql.subexpressionElimination.cache.maxEntries
     - 3.1.0
     - 100
     - The maximum entries of the cache used for interpreted subexpression elimination.
   * - spark.sql.subexpressionElimination.skipForShortcutExpr
     - 3.5.0
     - false
     - When true, shortcut eliminate subexpression with `AND`, `OR`. The subexpression may not need to eval even if it appears more than once. e.g., `if(or(a, and(b, b)))`, the expression `b` would be skipped if `a` is true.

Artifact(1)
~~~~~~~~~~~

.. list-table:: Artifact
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.artifact.copyFromLocalToFs.allowDestLocal
     - 4.0.0
     - <undefined>
     - | 
       | Allow `spark.copyFromLocalToFs` destination to be local file system
       |  path on spark driver node when
       | `spark.sql.artifact.copyFromLocalToFs.allowDestLocal` is true.
       | This will allow user to overwrite arbitrary file on spark
       | driver node we should only enable it for testing purpose.

View(1)
~~~~~~~

.. list-table:: View
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.view.maxNestedViewDepth
     - 2.2.0
     - 100
     - The maximum depth of a view reference in a nested view. A nested view may reference other nested views, the dependencies are organized in a directed acyclic graph (DAG). However the DAG depth may become too large and cause unexpected behavior. This configuration puts a limit on this: when the depth of a view exceeds this value during analysis, we terminate the resolution to avoid potential errors.

ColumnVector(1)
~~~~~~~~~~~~~~~

.. list-table:: ColumnVector
   :header-rows: 1

   * - Key
     - Since
     - Default
     - Description
   * - spark.sql.columnVector.offheap.enabled
     - 2.3.0
     - <value of spark.memory.offHeap.enabled>
     - When true, use OffHeapColumnVector in ColumnarBatch. Defaults to ConfigEntry(key=spark.memory.offHeap.enabled, defaultValue=false, doc=If true, Spark will attempt to use off-heap memory for certain operations. If off-heap memory use is enabled, then spark.memory.offHeap.size must be positive., public=true, version=1.6.0).
