@echo off
setlocal
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "TIMESTAMP=%dt:~0,8%-%dt:~8,6%"
set "BACKUP_DIR=backups"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
echo Stopping Neo4j...
docker compose stop neo4j
echo Creating backup...
docker compose run --rm -v "%cd%/backups:/backups" neo4j neo4j-admin database dump neo4j --to-path=/backups --overwrite-destination
move "%BACKUP_DIR%\neo4j.dump" "%BACKUP_DIR%\memgrap-%TIMESTAMP%.dump" 2>nul
echo Restarting Neo4j...
docker compose start neo4j
echo Backup complete: %BACKUP_DIR%\memgrap-%TIMESTAMP%.dump
