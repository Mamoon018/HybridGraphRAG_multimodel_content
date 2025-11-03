

from dataclasses import dataclass

from src.document_parsing.data_extraction import MinerU_Parser
from src.document_parsing.sample_data import combined_knowledge_units, current_multimodel_unit



"""
Utils Functions:

1- Knowledge units splitter
2- Context extractor for multi-modal content

"""
                        ##  1-  Knowledge units splitter  ##

# Define the function to split the knowledge units into textual and non-textual units

def units_splitter(knowledge_units_list:list):
    """
    This function takes the list of the knowledge units created in the parsing process from minerU output, and 
    filter out the textual and non-textual knowledge units on the basis of their content type, into two different
    objects. 

    **Args:**
    knowledge_units_list (list): It is the list of the knowledge units - combined textual and non-textual units.

    **Returns:**
    textual_knowledge_units (list): It is the list of the textual knowledge units.
    multi-model_knowledge_units (list): It is the list of the non-textual knowledge units.

    **Raises:**

    Implementation workflow:
    
    1- Initiate the two lists to store respective type of units separately.
    2- Iterate over the units using for loop 
    3- If content type is in ["title","text"]: append the list for textual knowledge units
    4- If content type == "table": append the list for non-textual knowledge units
    5- Return the textual_knowledge_units, non_textual_knowledge_units
    
    """

    # Initialize the minerU parser
    #### FREEZED FOR TESTING PURPOSE ####
    #init_minerU = MinerU_Parser(data_file_path=knowledge_units_list)
    #knowledge_units_list = init_minerU.format_minerU_output()

    complete_knowledge_units = knowledge_units_list

    # Initialize the lists for textual and non-textual units separately
    multi_model_units = []
    textual_units = []

    for unit in complete_knowledge_units:
        unit = dict(unit)

        # Fetch the textual units
        content_type = unit.get("content_type")
        if content_type in ["text","title"]:
            textual_units.append(unit)
        
        # Fetch the non-textual units
        elif content_type == "table":
            multi_model_units.append(unit)

    return multi_model_units,textual_units





                        ####  2-  Context Extractor  ####


class context_extractor():
    """
    It contains the context extractor for the provided chunk. It can process the Textual-chunk as well as Multi-model chunk to get
    the context around the provided chunk. 

    SCALED FORM OF CLASS - FINAL AFTER REFACTERICATION:
    Main function run:
    It aligns all the function together to run the context extractor
    
    Input source format:
    Atomic units content list (list): It is the list of the combined knowledge atomic units

    Output producer strategy:
    Chunks context (str): It is the approach where we will extract the chunks text that is surrounding the underneath text

    Final output formatting: 
    Truncate the text: It is for ensuring that generated context is within the token limits

    """
    def __init__(self,all_knowledge_units):

        self.all_knowledge_units:list[dict[str]] = combined_knowledge_units

    
    # Create the context extractor for multi-model content
    def multi_model_context_extractor(self, multi_model_knowledge_units:list[dict[str]]):

        """
        It takes the multi-model atomic unit list, fetches the details of the multi-model content such as index on page 
        and page number. It will access the combined knowledge units & will extract the units around the given content.

        **Args:**
        multi_model_knowledge_units (list[dict[str]]): It is the list of multi-model atomic units
        combined_knowledge_units (list[dict[str]]): It is the list of the comined textual and multi-model atomic units. 

        **Returns:**
        chunk_context (list[str]): It is the list of the chunks surroudning the content.

        """

        # Call the input variables 
        multi_model_units = multi_model_knowledge_units
        combined_atomic_units = self.all_knowledge_units

        # fetches the information of the current unit 
        current_unit = current_multimodel_unit
        for chunk in current_unit:
            
            if "table_image_path" in chunk:
                page_of_chunk = chunk.get("page_no.","")
                index_of_current_chunk = chunk.get("index_on_page","")
                table_image_path = chunk.get("table_image_path","")
            elif "table_caption" in chunk:
                page_of_chunk = chunk.get("page_no.","")
                index_of_current_chunk = chunk.get("index_on_page","")
                table_caption = chunk.get("table_caption","")
        
        # get the surrounding chunks from the combined atomic units dict
        """
        Surrounding chunks:
        0- Initialize the list to store the contextual (Done)
        1- Use the current unit info details to get the current page number (Done)
        2- Calculate the previouse page number and the next page number (Done)
        3- Get the list of the number of indexes on the current page (Done)
        4- check if index of the current unit is minima = (minim or minim + 1) or maxima = (maximum - 1) index of the page (Done)
        5- If current chunk neither lies in minima nor maxima index of the current page then just take two next and two previouse chunks (Done)
        6- If lies in minima zone, then filter out the units of previous page.
        7- fetch the last two units of previous page
        8- If lies in maxima zone, then filter out the units of next page
        9- fetch the first two units of next page
        In this way, we will be able to get the surrounding units required to extract the context 
        """

        list_chunks_for_context_extraction = []

        current_page = page_of_chunk
        previous_page = page_of_chunk - 1
        next_page = page_of_chunk + 1

        # Fetch all the units for the current page
        units_of_current_page = [unit for unit in combined_atomic_units if unit["page_no."] == current_page]
        

        # Calculate minima & maxima zone
        for indexes in units_of_current_page:
            count =+ 1
            index_of_current_page = indexes["index_on_page"]
            if count == 1:
                lowest_index_of_page = index_of_current_page

        maximum_index_of_page = index_of_current_page
        minima = lowest_index_of_page + 1
        maxima_zone = maximum_index_of_page - 2

        # Based on the placement of the current chunk, we will extract the surrounding chunks
        if index_of_current_chunk > maxima_zone:
            need_to_extract_from_next_page = True
        else:
            need_to_extract_from_next_page = False
            need_to_extract_from_current_page = True
        if index_of_current_chunk < minima:
            need_to_extract_from_previous_page = True
        else: 
            need_to_extract_from_previous_page = False 
            need_to_extract_from_current_page = True
        
        # Extract the list of chunks
        list_of_context_chunks = []
        
        if need_to_extract_from_next_page:
            # check how many chunks do we have before the next heading starts on the next page
            units_of_next_page = [units for units in combined_atomic_units if units["page_no."] == next_page]
            units_of_next_page = sorted(units_of_next_page, key= lambda x:x["index_on_page"], reverse=True)
            """
            1- Loop over the units of the next page
            2- if content is "text", add it to the list of context chunks
            3- else terminate the loop and end the appending of chunks to the list of context chunks
            """
            count = 0
            for unit_of_NP in units_of_next_page and count < 3:
                count =+ 1
                if unit_of_NP["content_type"] == "text":
                    chunk_of_NP = unit_of_NP.get("raw_content","")
                    list_of_context_chunks.append(chunk_of_NP)
                else:
                    break

            # check how many chunks do we have to before the previous heading on the previous page
        if need_to_extract_from_previous_page:
            units_of_previous_page = [units for units in combined_atomic_units if units["page_no."] == previous_page]
            units_of_previous_page = sorted(units_of_previous_page, key=lambda x:x["index_on_page"], reverse=True)

            for unit_of_PP in units_of_previous_page:
                count = 0
                if unit_of_PP["content_type"] == "text" and count < 3:
                    count =+ 1
                    chunk_of_PP = unit_of_PP.get("raw_content","")
                    list_of_context_chunks.append(chunk_of_PP)
                else:
                    break
        
        if need_to_extract_from_current_page:
            # We have already calculated units for current page
            """
            1- Using the index of current chunk, we will find out previouse two chunks & next two chunks.
            2- iterating_chunk = 0
            3- Inside the loop, for every text chunk, update iterating_chunk = ICC - 
            """
            # Previous chunks of current page
            count = 1
            index_previous_chunk_of_CP = index_of_current_chunk - count
            for unit_of_CP in units_of_current_page:
                if unit_of_CP["index_on_page"] == index_previous_chunk_of_CP:
                    count =+ 1
                    if unit_of_CP["content_type"] == "text" and count < 3:
                        previous_chunk_of_CP = unit_of_CP.get("raw_content","")
                        list_chunks_for_context_extraction.append(previous_chunk_of_CP)                
                    else:
                        break
            # Next chunks of current page
            count = 1
            index_next_chunk_of_CP = index_of_current_chunk + count
            for unit_of_CP in units_of_current_page:
                if unit_of_CP["index_on_page"] == index_previous_chunk_of_CP:
                    count =+ 1
                    if unit_of_CP["content_type"] == "text" and count < 3:
                        next_chunk_of_CP = unit_of_CP.get("raw_content","")
                        list_chunks_for_context_extraction.append(next_chunk_of_CP)                
                    else:
                        break

            
        
        return print(list_of_context_chunks)


if __name__ == "__main__":

    multi_model_knowledge_units, textual_knowledge_units = units_splitter(knowledge_units_list=combined_knowledge_units)

    extractor = context_extractor(all_knowledge_units=combined_knowledge_units)
    extractor.multi_model_context_extractor(multi_model_knowledge_units=multi_model_knowledge_units)