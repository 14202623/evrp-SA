all: main

main: main.o heuristic.o EVRP.o stats.o 
	g++ main.o heuristic.o EVRP.o stats.o -o main

main.o: main.cpp
	g++ -c main.cpp

heuristic.o: heuristic.cpp
	g++ -c heuristic.cpp

EVRP.o: EVRP.cpp
	g++ -c EVRP.cpp

stats.o: stats.cpp
	g++ -c stats.cpp


clean: 
	rm -rt *o main
