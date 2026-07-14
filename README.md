# Obiettivo

Questa repository contiene il codice sorgente dell'applicativo Easy Polls, i manifest Kubernetes necessari al suo deployment e il workflow di CI/CD che ne automatizza la build e il rilascio all'interno del cluster situato in AWS.

### Applicativo

L'applicativo è un'applicazione web per la creazione di sondaggi istantanei: un utente crea una domanda con alcune opzioni di risposta, ottiene un link condivisibile, e chiunque abbia il link può votare. I risultati sono visualizzabili in una pagina dedicata, che si aggiorna in tempo reale mostrando le percentuali di voto. L'applicazione è divisa in tre componenti, più il database MongoDB:
 - `frontend`: interfaccia web statica per la creazione dei sondaggi.
 - `poll-service`: espone l'API per la creazione dei sondaggi e la registrazione dei voti.
 - `results-service`: espone l'API per la restituzione dei risultati di un determinato sondaggio.

Il database è **Amazon DocumentDB**, un servizio gestito compatibile con MongoDB, situato all'esterno del cluster: nella repository non è quindi presente alcun manifest relativo alla persistenza dei dati.\
L'`HorizontalPodAutoscaler` è configurato esclusivamente sul `results-service`, che scala in base all'utilizzo di CPU.

## Struttura della repository

```
├── frontend
│   ├── Dockerfile
│   └── html
│       ├── app.css
│       ├── index.html
│       ├── results.html
│       └── vote.html
├── k8s
│   ├── frontend-deployment.yml
│   ├── frontend-service.yml
│   ├── ingress.yml
│   ├── poll-service-deployment.yml
│   ├── poll-service-service.yml
│   ├── results-service-deployment.yml
│   ├── results-service-scaling.yml
│   └── results-service-service.yml
├── poll-service
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
└── results-service
    ├── Dockerfile
    ├── app.py
    └── requirements.txt
```

### Directory k8s

La directory `k8s` contiene i manifest Kubernetes che descrivono lo stato desiderato dell'applicativo all'interno del cluster. In particolare:
 - I manifest relativi al `frontend` definiscono il `Deployment` del frontend, con due repliche, e il relativo `Service` di tipo `ClusterIP`. L'instradamento delle chiamate API è gestito dall'Ingress.
 - I manifest relativi al `poll-service` definiscono il `Deployment` del servizio, con due repliche, e il relativo `Service` di tipo `ClusterIP`.
 - I manifest relativi al `results-service` definiscono il `Deployment` del servizio, il relativo `Service` di tipo `ClusterIP` e l'`HorizontalPodAutoscaler`, che scala il numero di repliche da $2$ a $6$ in base all'utilizzo medio di CPU.
 - `ingress.yml` definisce la risorsa `Ingress`, che descrive le regole di instradamento delle richieste in base al prefisso del path e vengono gestite dall'Ingress Controller nginx, in ascolto sulla NodePort $30080$ dei nodi del cluster.

Nei manifest vengono utilizzati tre *placeholder*, che vengono sostituiti dal workflow di deployment al momento del rilascio, dopo che l'infrastruttura è stata creata:
 - `ECR_REGISTRY`: l'indirizzo del registry ECR.
 - `IMAGE_TAG`: il tag dell'immagine, corrispondente all'hash del commit.
 - `DOCDB_ENDPOINT`: l'endpoint del cluster DocumentDB.

### Workflows

La directory `.github/workflows` contiene il workflow di CI/CD dell'applicativo. È presente un solo workflow:ù
 - `deploy.yml`: si attiva a seguito di un push sul branch `main`, oppure manualmente, ed è inoltre triggerato automaticamente dal workflow di provisioning dell'infrastruttura al termine della configurazione del cluster. Si occupa di effettuare la build delle tre immagini dei container e pubblicarle su Amazon ECR, marcandole con l'hash del commit, creare il secret di Kubernetes `mongo-secret` a partire dal segreto `MONGO_PASSWORD` della repository e sostituire i *placeholder* all'interno dei manifest e applicarli al cluster, attendendo infine il completamento del rollout.

---

# Setup

### Creazione dell'environment e dei segreti

Affinché il workflow di deployment funzioni correttamente, è necessario creare un environment e aggiungere dei segreti. Per creare l'environment, è sufficiente andare su `Settings > Environments > New environment` chiamandolo `production` e, una volta creato, è possibile aggiungere i segreti cliccando su `Add environment secret` in `Environment secrets` e aggiungere:
 - `AWS_ROLE_ARN`: corrisponde all'ARN del ruolo IAM creato precedentemente.
 - `BASTION_SSH_PRIVATE_KEY`: occorre utilizzare la chiave privata del Bastion Host generata per la repository dell'infrastruttura.
 - `MONGO_PASSWORD`: corrisponde alla password che verrà usata per l'istanza di DocumentDB.

### Deployment nel cluster

A seguito di ogni nuovo push, oppure al completamento del workflow di provisioning dell'infrastruttura, il workflow di deployment si occuperà di applicare i manifest Kubernetes e aspettare il rollout della nuova versione.