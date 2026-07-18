run:
	uv run python assistant.py

chat:
	uv run streamlit run app.py

dashboard:
	uv run streamlit run dashboard.py --server.port 8502

generate-data:
	uv run python generate_data.py

network:
	docker network create monitoring

postgres: 
	docker run -it \
		--name course-assistant-pg \
		--network monitoring \
		-e POSTGRES_USER=user \
		-e POSTGRES_PASSWORD=password \
		-e POSTGRES_DB=course_assistant \
		-p 5432:5432 \
		-v pgdata:/var/lib/postgresql/data \
		postgres:17

grafana: 
	docker run -d \
    --name grafana \
    --network monitoring \
    -p 3100:3000 \
    -v grafana_data:/var/lib/grafana \
    grafana/grafana