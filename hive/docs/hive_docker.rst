Using Hive w/ Docker
====================

.. toctree::
   :maxdepth: 2

.. code-block:: shell
   :caption: Start HiveServer2

   docker run -d -p 10000:10000 -p 10002:10002 --env SERVICE_NAME=hiveserver2 --name hiveserver2 apache/hive:4.0.0

.. code-block:: shell
   :caption: Stop HiveServer2

   docker rm hiveserver2

.. code-block::
   :caption: Start beeline

   docker exec -it hiveserver2 beeline -u 'jdbc:hive2://localhost:10000/'


