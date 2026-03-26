@echo off
setlocal
if "%~1"=="" (echo Usage: scripts\restore.bat ^<path-to-dump-file^> & exit /b 1)
if not exist "%~1" (echo Error: File not found: %~1 & exit /b 1)
echo WARNING: This will overwrite the current Neo4j database!
set /p confirm=Continue? [y/N]
if /i not "%confirm%"=="y" (echo Aborted. & exit /b 0)
echo Stopping Neo4j...
docker compose stop neo4j
echo Restoring...
docker compose run --rm -v "%~dp1:/restore" neo4j neo4j-admin database load neo4j --from-path=/restore --overwrite-destination
echo Restarting Neo4j...
docker compose start neo4j
echo Restore complete.
