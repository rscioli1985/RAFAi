We are starting a new project. 

I want to be able to build a RAG engine for Name Image Likeness (NIL) based content. 

The primary goal of this application is to be able to build a repository of NIL based questions that can be answers with an AI agent.  This project will represent an MVP/Proof of concept.  Eventually it will be handed off to an engineering team to manage, and productionalize.  The application will be built in python.  

As an MVP, we will start with a reddit scraping bot that can query reddit's API, and Identify topics that are related to NIL.  

Our object is to identify frequently asked questions about NIL using reddit as a primary source. 

We will need to have a set of basic scripts that we can run. 

We will need a cron based scheduler that can be run on a daily basis to identify new reddit threads. 

We will provide a set of reddit subreddits that are going to be polled regularly for updated content. 

We will need an operational database that can store the data.  We should create a postgres data base using docker that can be used for this purpose.  

We will need a vector database that can be used for retrieval augmented generation. 

we will need secrets to be managed outside of this directory.  They will be referenced in a .env file that we will create within this directory.  We will store them as yaml files in a separate directory and use absolute paths so that the application is able to use them. 


Reddit API keys will be stored in our secrets directory outside of this library.

we will need to build a very basic AI agent in a react app.  We should front the front end in node. 

Questions: 
What is our recommended backend architecture? Should we be building this using Flask or Fast API?  the primary consumer facing use case is an AI agent, so development of streaming use cases is a priority. 

We will need to have a rest API for storage and management of the application. 

As a Sr. Product Manager and an expert in developing AI applications, generate a detailed product requirements document that outlines the core use cases that we are trying to achieve. 

Review this intial prompt: docs/tech-stack/initial-prompt.md

Create a detailed product requirements document in this directory: docs/tech-stack/product-requirements

As part of your product requirements document, include a list of open questions that I will respond to, to provide additional product clarifications. 