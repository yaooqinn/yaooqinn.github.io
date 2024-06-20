Data Types
==========

The differences between Spark and Hive data types could be categorized into the following types:

.. list-table:: The differences between Spark and Hive Data Types
   :widths: auto
   :align: center
   :header-rows: 1

   * - KEYWORD
     - Spark
     - Hive
     - Compatible
     - Description
     - Differences
   * - TINYINT
     - Y
     - Y
     - Y
     - 1-byte signed integer numbers, [-128, 127].
     -
   * - BYTE
     - Y
     - **N**
     - **N**
     - Alias for TINYINT
     - Hive does not support BYTE
   * - SMALLINT
     - Y
     - Y
     - Y
     - 2-byte signed integer numbers, [-32768,32767].
     -
   * - SHORT
     - Y
     - **N**
     - **N**
     - Alias for SMALLINT
     -
   * - | INT
       | INTEGER
     - Y
     - Y
     - Y
     - 4-byte signed integer numbers, [-2147483648, 2147483647].
     -
   * - BIGINT
     - Y
     - Y
     - Y
     - 8-byte signed integer numbers, [-9223372036854775808, 9223372036854775807].
     -
   * - LONG
     - Y
     - **N**
     - **N**
     - Alias for BIGINT
     -
   * - | FLOAT
       | REAL
     - Y
     - Y
     - Y
     - 4-byte single precision floating point numbers.
     -
   * - DOUBLE
     - Y
     - Y
     - Y
     - 8-byte double precision floating point numbers.
     -
   * - DOUBLE PRECISION
     - **N**
     - Y
     - **N**
     - Alias for DOUBLE
     -
   * - | DECIMAL
       | DEC
       | NUMERIC
     - Y
     - Y
     - Y
     - Arbitrary precision decimal numbers.
     - NUMERIC added in Hive since 3.0.0 and Spark since 3.0.0
   * - STRING
     - Y
     - Y
     - Y
     - Variable-length character string.
     -
   * - CHAR(n)
     - Y
     - Y
     - **N**
     - Fixed-length character string.
     - `n` is allowed [1, 255] in Hive, while [1, 2147483647] in Spark
   * - CHARACTER(n)
     - Y
     - **N**
     - **N**
     - Alias for CHAR(n)
     - Hive does not support CHARACTER(n)
   * - VARCHAR(n)
     - Y
     - Y
     - **N**
     - Variable-length character string.
     - `n` is allowed [1, 65535] in Hive, while [1, 2147483647] in Spark
   * - BINARY
     - Y
     - Y
     - Y
     - Variable-length binary string.
     -
   * - DATE
     - Y
     - Y
     - Y
     - A date type.
     -
   * - TIMESTAMP
     - Y
     - Y
     - **N**
     - A timestamp type.
     - In Hive, it's `TIMESTAMP WITHOUT TIME ZONE`, while in Spark, it's `TIMESTAMP WITH LOCAL TIME ZONE`
   * - TIMESTAMP WITH LOCAL TIME ZONE
     - **N**
     - Y
     - **N**
     - A timestamp with local time zone type
     - In Spark, `TIMESTAMP` represents the `TIMESTAMP WITH LOCAL TIME ZONE` but the keyword is not available
   * - TIMESTAMP_LTZ
     - Y
     - **N**
     - **N**
     - A timestamp with local time zone type
     -
   * - TIMESTAMP_NTZ
     - Y
     - **N**
     - **N**
     - A timestamp without time zone type
     -
   * - ARRAY<element_type>
     - Y
     - Y
     - Y
     - A collection of elements.
     -
   * - MAP<key_type, value_type>
     - Y
     - Y
     - **N**
     - A collection of key-value pairs.
     - In Hive, the key type is limited to primitive types, while in Spark, it can be any type
   * - STRUCT<field_name : field_type [COMMENT field_comment], ...>
     - Y
     - Y
     - Y
     - A structure of named fields.
     -
   * - UNIONTYPE<...>
     - **N**
     - Y
     - **N**
     - A collection of types.
     -
