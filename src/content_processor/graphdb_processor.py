

from src.document_parsing.sample_data import sample_textual_vectorized_payload_insertion_list, sample_multi_modal_vectorized_payload_insertion_list, Milvus_extracted_multimodal_chunks
from src.utils import Milvus_client, perplexity_llm, neo4j_dbconnection, doc_id, starting_time, ending_time
from src.document_parsing.sample_data import Parent_entity_info
from src.content_processor.prompt import ENTITIES_GENERATOR_PROMPT
from pymilvus import MilvusException
import os 
import perplexity
import re


perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

class graphdb_processor():
    """
    It contains the methods that processes atomic units (textual & non-textual) in order to generate neo4j knowledge
    graph.
    1- Get the chunk from the VDB.
    2- PROMPT the LLM to extract the entities, relationships along with their description and content keywords.
    3- Format the output of the LLM - into dicts containing entities info as well as metadata. 
    4- Create the relationships with the Parent entity info generated with atomic units (Only for Multi-nomial Info KG)
    5- Push the data to the Graph database 
    """

    def __init__(self, textual_VBD_extracted_chunk, multi_modal_VDB_extracted_chunks):
        self.textual_VBD_extracted_chunk = textual_VBD_extracted_chunk
        self.multi_modal_VDB_extracted_chunks = multi_modal_VDB_extracted_chunks
        self.milv_client = None

    def __run_graphdb_processor__(self):
        """
        It initializes the different behaviors of the graphdb_process class by calling its method to act 
        upon the data it has received. It is the function that orchestrates the implementation of the
        class.
        """
        try:
            # Get the multi-modal chunks
            milvus_chunks = self.multi_modal_info_extraction_for_KG()
            #print(f"Milvus chunks -->  {milvus_chunks}")

            #KG_entities, parent_entity_info = self.entities_generation_for_multimodal_chunks(milvus_extracted_data= milvus_chunks)
            #print(f"KG_entities --> {KG_entities}")

            entities, relationships = self.entities_relationship_parsing()
            #print(f"Parsed entities --> {entities}")

            entities_with_id,relationships_with_id = self.parent_child_relationships(entity_nodes=entities, relationship_edges=relationships,
                                                    parent_entity_node=Parent_entity_info)
            #print(f" -- entities and relationships with IDs -- {entities_with_id}, {relationships_with_id}")


            KG_entity_query, KG_relationship_query  = self.knowledge_graph_query_generator(entity_nodes=entities_with_id,relationship_edges= relationships_with_id)

            #final_kg_overview = self.cypher_query_executor(queries_for_entities=KG_entity_query, queries_for_relationships= KG_relationship_query)

            return print(f"Here are the parsed relationships {KG_entity_query}")
        
        except Exception as e:
            raise(f"error occurred in __run__graphdb_processor__ due to {e}") from e 
 

    def multi_modal_info_extraction_for_KG(self):
        """
        It takes the multi-modal atomic units, entity info and entity summary of those units.
        1- Atomic unit will be extracted from the VDB. (Done)
        BEFORE:  Entity info and Entity summary of multi-modal content from metadata of VDB. (Done)

        **Args:**
        Multi_modal_atomic_units (list[dict]): It is the list of content units, which contains decription and other metadata related fields.

        **Returns:** 
        entities (list[dict]): It is the list of entities along with their details.
        relationships (list[dict]): It is the list of relationships between entities along with details explaining those relationships.

        Entities Extraction --> 
        1- Entity type : Person, Event, Organization, role, device, disease, inst

        """
        try:

            # Extract the multi-modal chunks from Milvus VDB
            # For Sampling Purpose, we will use saved extracted data.
            Milvus_extracted_multimodal = Milvus_extracted_multimodal_chunks
            """
            self.milv_client = Milvus_client()

            multi_model_milvus_extracted_chunks = self.milv_client.query(
                collection_name= "Multi_modal_VDB_collection",
                output_fields=["chunk_id", "doc_id", "raw_content", "metadata"],
                limit = 2
            )
            """
            

            return Milvus_extracted_multimodal

        except MilvusException as e:
            raise(f"Error occurred in Milvus_query_extraction operation due to {e}") from e 

    
    def entities_generation_for_multimodal_chunks(self,milvus_extracted_data):

        """
        1- Fetch the entity info that needs to be passed to LLM.
        2- Feeds content_of_chunk, parent_entity_name, and parent_entity_type to the LLM the atomic unit to extract entities and relationships between them. 
        3- In particular for multi-model units, an entity info of figure (Table,Image etc) is going to be considered
           as the Parent-node. Whereas, entities extracted from the entity description will be considered child-nodes.
        4- We will create the relationship of child-nodes with parent nodes.
        5- From the atomic unit content, some 'content keywords'(high level) will also be extracted.
        6- Push the data to the Graph Database for the creation of knowledge Graph.
        """


        # Compose the Parent entity info 
        content_of_chunk = milvus_extracted_data.get("raw_content",[])
        id_of_chunk = milvus_extracted_data.get("chunk_id",[])
        meta_data_of_chunk = milvus_extracted_data.get("metadata",[])
        entity_summary_of_chunk = meta_data_of_chunk.get("entity_summary",[])
        for i in entity_summary_of_chunk:
            Parent_entity_name = i.get("entity_name",[])  # NEED TO FIX THE STRUCTURE OF ENTITY SUMMARY: It should not be list!!
            Parent_entity_type = i.get("entity_type",[])

        parent_entity_info:dict = {
            "parent_entity_name":Parent_entity_name,    # NEED TO FIX THE STRUCTURE OF PARENT ENTITY INFO - sample data contains correct structure as sample.
            "parent_entity_type": Parent_entity_type, 
            "content": content_of_chunk,
            "id_of_chunk": id_of_chunk
            }
        
        # Extract entities using LLM
        perplexity_client = perplexity_llm(api_key=perplexity_api_key,
                                           retries=1)
        
        prompt = ENTITIES_GENERATOR_PROMPT

        try:
            # Generate perplexity response
            llm_content_description = perplexity_client.chat.completions.create(
                messages= 
                        [
                            {
                                "role": "user", 
                                "content" :  
                                    [ 
                                        {
                                            "type" : "text",
                                            "text": prompt
                                        },
                                        {
                                            "type": "text",
                                            "text": f"here is the input text: {content_of_chunk}"
                                        }
                                    ]
                            }
                        ],
                model= "sonar"

            )

            KG_material = llm_content_description.choices[0].message.content

            # For testing purpose.
            with open("LLM_extraction_output.txt", "w", encoding= "utf-8") as f:
                f.write(KG_material)
            
            return KG_material, parent_entity_info


        except perplexity.BadRequestError as e:
            print(f"Invalid request parameters: {e}")
        except perplexity.RateLimitError as e:
            print("Rate limit exceeded, please retry later")
        except perplexity.APIStatusError as e:
            print(f"API error: {e.status_code}")

    def _parse_entities(self,match):
        """
        It parses the llm ouptut, and returns the transformed structured of entity nodes. 
        """
        return {
                    "entity_type" : match.group(2),
                    "properties": {
                        "entity_name" : match.group(1),
                        "entity_description" : match.group(3)
                    }     
                }
    
    def _parse_relationships(self,match):
        """
        It parses, and returns the transformed structure of relationship edges. 
        """
        return {
                    "source": match.group(1),
                    "target": match.group(2),
                    "properties": {
                        "description": match.group(3),
                        "keywords": match.group(4),
                        "category": match.group(5)
                    }
                }

    

    def entities_relationship_parsing(self):
        """
        This function takes the text output of the llm which contains the entities, relationships and context keywords
        for a given chunk - transforms it into the dict structure to make it useful for building the knowledge graph
        in Neo4j.

        **Args:**
        llm_entity_relation_output (text): It is the text output where entities, relationships and context keywords are separated by the delimeter.

        **Returns:**
        entities list[dict]: It is the list of the extracted entities.
        relationships list[dict]: It is the list of the relationships edges that will be used to connect entities with each other.
        chunk_context_keywords (list): It is the list of the keywords that contains crux of the chunk text. It will keep context around an entity entact with it. 

        """
        llm_entity_relation_output = None

        # Read the output
        with open("LLM_extraction_output.txt","r", encoding= "utf-8") as readLLMOutput:
            llm_entity_relation_output = readLLMOutput.read()
        llm_output_sectioned =  [ i.strip() for i in llm_entity_relation_output.split("##") ]
        
        # Define the lists to store the transformed output
        entities = []
        relationships = []
        entity_name_id = {}
        
        # Define the regex pattern to check the 
        pattern_entity = re.compile('\("entity"<\|>"(.*?)"<\|>"(.*?)"<\|>"(.*?)"\)')
        pattern_relationship = re.compile('\(\s*["\']?relationship["\']?\s*<\|>\s*["\']?(.*?)["\']?\s*<\|>\s*["\']?(.*?)["\']?\s*<\|>\s*["\']?(.*?)["\']?\s*<\|>\s*["\']?(.*?)["\']?\s*<\|>\s*["\']?(.*?)["\']?\s*\)')

        for record in llm_output_sectioned:
            if entity_match:= pattern_entity.search(record):
                entities.append(self._parse_entities(match=entity_match)) 
            elif relationship_match:= pattern_relationship.search(record):
                relationships.append(self._parse_relationships(match=relationship_match))
        
        # Mapping entities with their entity types
        for entity in entities:
            entity_type = entity["entity_type"]
            entity_name = entity["properties"]["entity_name"]
            entity_name_id[entity_name] = entity_type

        # Assigning types to source and target entities
        for relat in relationships:
            relat["source_entity_type"] = entity_name_id[relat['source']]
            relat["target_entity_type"] = entity_name_id[relat['target']]   

        return entities, relationships

    
    # ID assigner for entities, relationships so, we can store them in KG with unique IDs
    def _id_generator(self,name):
        """Generate ID for an object"""
        document_id = doc_id()
        return f"{name}_{document_id}"
    
    # Parent_child node relationship generator 
    def _relationship_generator(self,entity, parent_entity):
        """
        It creates the relationships between the entities and add them into relationships object. Mainly
        this will be used for creating relationships between parent and child nodes.
        """

        child_entity = entity["properties"]["entity_name"]
        child_entity_type = entity["entity_type"]
        parent_entity_type = entity["entity_type"]
        parent_entity = parent_entity["properties"]["entity_name"]

        
        if child_entity != parent_entity:
            relationship_edge_generated = {
                        "source": child_entity,
                        "target": parent_entity,
                        "source_entity_type": child_entity_type,
                        "target_entity_type": parent_entity_type,
                        "properties": {
                                        "description": f"{child_entity} is child-entity that belongs to parent-entity {parent_entity}", 
                                        "category": "Main-theme"
                                        }
                                }
        
        # Add to relationship_edges 
            return relationship_edge_generated
        
        return None




    # Function for the adding IDs into extracted entities and relationships
    def parent_child_relationships(self,entity_nodes, relationship_edges, parent_entity_node):
        """
        1- It assigns IDs to entity_nodes and relationship_edges. 
        2- It takes the entity_nodes and create belongs to relationships with parent entity_node & add it to the relationship_edges.

        **Args:**
        entity_nodes (list): It is the list of the extracted entities.
        relationship_edges (list): It is the list of the relationships between the extracted entities. 
        parent_entity_node (dict): It is the details of the parent entity from which all entities & relationships have been extracted.
        
        """
        entities_with_ids = []

        # Generate ID for entities
        for entity in entity_nodes:
            entity["entity_id"] = self._id_generator(name="entity")
            # Add chunk ID for reference in entities and relationships
            entity["properties"]["id_of_chunk"] = parent_entity_node["id_of_chunk"]
            entities_with_ids.append(entity)
        
        # Add parent entity details in entity nodes so, it also gets created in knowledge graph.
        entities_with_ids.append(parent_entity_node)

        
        relationships_with_ids = relationship_edges
        # Add relationship between parent and child nodes in relationships to object that already contains child entities relationships
        for entity in entity_nodes:
            additional_edge = self._relationship_generator(entity=entity, parent_entity=Parent_entity_info)
            if additional_edge is not None:
                relationships_with_ids.append(additional_edge)

        # Generate ID for relationships
        for relationship in relationships_with_ids:
            relationship["relaionship_id"] = self._id_generator(name="relationship")

        return entities_with_ids, relationships_with_ids



    # Cypher Query generator
    def knowledge_graph_query_generator(self, entity_nodes, relationship_edges):
        """
        It takes the entities and relationships and runs the cypher query to push them into the knowledge graph
        of graph database. 

        Building KG:
        1- Get the entities_with_ids object. 
        2- Create the variables that we need to pass onto the cypher query. (For Nodes & Properties)
        3- Write a cypher query for entities.
        4- SEPARATE FUNCTION Apply for loop, that takes each object (Nodes & relationships) and executes cypher query for it. 

        **Args:**
        entity_nodes (list[dict]): It is the list of entity nodes
        relationships (list[dict]): It is the list of the relationships edges

        **Returns:**
        query_execution_confirmation (str): Confirmation about the execution of the query.

        """
        try:
            entity_cypher_query = []
            entity_name_id = {}

            # Entity Cypher Query
            for entity in entity_nodes:
                # Entity variables
                node_type = entity.get("entity_type",[])
                node_id = entity.get("entity_id",[]) or entity.get("id_of_chunk",[]) 
                node_name = entity["properties"]["entity_name"].replace("#","").replace(" ","").replace(".","")
                
                entity_name_id[node_name] = node_id

                entity_cypher = f" MERGE ( n: {node_type} {{node_id : '{node_id}'}})"

                # Entity Properties
                properties = entity.get("properties",[])
                entity_properties = ",".join([f"n.{key} = '{value}'" for key,value in properties.items()])

                entity_cypher += f" ON CREATE SET {entity_properties} " 
                entity_cypher_query.append(entity_cypher)
            


            # Relationships Cypher Query
            relationship_cypher_query = []

            for relationship in relationship_edges:
                # source, target, id, description, keywords,type
                """
                Query format:
                MATCH (s:source_node_type {node_id: entity_id})
                MATCH (t:target {node_id: entity_id})
                CREATE (s)-[: BELONGS_TO ]->(t)
                """
# Error because Parent node is not present in the entity list so, cannot extract its id.
                source_node = relationship.get("source",[]).replace("#","").replace(" ","").replace(".","")
                target_node = relationship.get("target",[]).replace("#","").replace(" ","").replace(".","")
                source_node_type = relationship.get("source_entity_type",[]).replace("#","").replace(" ","").replace(".","")
                target_node_type = relationship.get("target_entity_type",[]).replace("#","").replace(" ","").replace(".","")
                relationship_properties = relationship["properties"]
                source_node_id = entity_name_id[source_node]
                target_node_id = entity_name_id[target_node]
                relationship_properties_extr = ",".join([f"{key}:'{value}'" for key,value in relationship_properties.items()])


                relationship_cypher = f"MATCH (s:{source_node_type} {{node_id:'{source_node_id}'}}) MATCH (t:{target_node_type} {{node_id:'{target_node_id}'}}) MERGE (s)-[:BELONGS_TO {{{relationship_properties_extr}}}]->(t)"            
                relationship_cypher_query.append(relationship_cypher)
            

            return entity_cypher_query, relationship_cypher_query
        
        except Exception as e:
            raise RuntimeError(f"Error occurred in knowledge graph buildwer due to {e}") from e 


    # Cypher query executor
    def cypher_query_executor(self, queries_for_entities:list, queries_for_relationships:list):
        """
        It takes the entities generation and relationships generator cypher queries and executes the queries 
        using neo4j Graph database. 

        **Args:**
        queries_for_entities (list): It is the list of entity generation queries for all extracted entities.
        queries_for_relationships (list): It is the list of relationship generation queries between extracted entities.

        **Return:**
        confirmation about execution of cypher query.

        Plan of Action:
        1-  Get the neo4j instance initializer
        2- Execute the queries for entities to generate entities in knowledge graph
        3- Execute the queries for relationships to create relationships between entities of knowledge graph
        
        """

        # Neo4j initializer
        neo4j_db = neo4j_dbconnection()

        # list of nodes created
        nodes_of_KG = []

        # Execute the query for entity generation in knowledge graph
        for query in queries_for_entities:
            execution_summary = neo4j_db.execute_query(query_=query, database_="neo4j").summary

            nodes_created = execution_summary.counters.nodes_created
            nodes_of_KG.append(nodes_created)
        
        # list of relationships created 
        relationships_of_KG = []
        # Execute query for relationship generation between entities in knowledge graph
        for query in queries_for_relationships:
            execution_summary = neo4j_db.execute_query(query_=query, database_="neo4j").summary

            nodes_created = execution_summary.counters.relationships_created
            relationships_of_KG.append(nodes_created)
        
        return nodes_of_KG








## Final Run of Graphdb Processor

graphdb = graphdb_processor(textual_VBD_extracted_chunk=sample_textual_vectorized_payload_insertion_list,
                            multi_modal_VDB_extracted_chunks=sample_multi_modal_vectorized_payload_insertion_list)

graphdb.__run_graphdb_processor__()










