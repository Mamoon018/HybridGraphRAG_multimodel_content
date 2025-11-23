
from src.document_parsing.sample_data import combined_knowledge_units, multi_model_knowledge_units




                        ####  2-  Context Extractor  ####

class Context_Extractor():
    """
    It contains two components required for driving the context around the multi-model context. 
    1) Context Extractor 
    2) multi-model Prcoessor

    1) Context extractor takes the current chunk (multi-model chunk), fetches the text from the surrounding of the current chunk.

    2) multi-model Processor: It takes the image of multi-model content, and text fetched by the context extractor & get the 
        description of the multi-model content & details of entity name & other details required to store it in Knowledge Graph.

    """
    def __init__(self):

        self.all_knowledge_units:list[dict[str]] = combined_knowledge_units
        self.multi_model_units = multi_model_knowledge_units

    def __run_context_extractor__(self) -> list[dict]:

        # multi_model_units with context contextual_chunks_text
        multi_model_units_with_contextual_chunks = []

        for unit in self.multi_model_units:
            if "table_image_path" not in unit:
                continue
            context_chunks_text = self.multi_model_extractor(current_multi_model_unit=unit)
            unit["contextual_text"] = context_chunks_text
            multi_model_units_with_contextual_chunks.append(unit)

        return multi_model_units_with_contextual_chunks

    
    def multi_model_extractor(self,current_multi_model_unit:list[dict[str]]):
        """
        It takes the current unit, and fetches its placement details to identify the surrouding chunks in the documents and then 
        place them in the chunks for context extraction list.

        Here is the workflow:
        1- Find out the page of current chunk. Using that, find out previous page and next page. (Done)
        2- Access all chunks of current page, extract their index numbers and store in a list in their hierarchical order. (Done)
        3- Access all chunks of the next page, and of the previous page. Extract their index numbers and store separately. (Done)
        4- Put them together in a single list (Done)
        5- Fetch the next two & previous two chunks of the current chunk from this list.
            (a) loop over the list to find out the current chunk (Done)
            (b) Findout the index of the current chunk in the list (Done)
            (c) Fetch the previous two chunks and next two chunks from the units (Done)
            (d) Fetch text from the shortlisted surrounding chunks using chunk-context-window
        
        Detect source type --> Source Handler --> Windowing --> Extract --> Truncate
                
        """

        # Input variables
        all_knowledge_units = self.all_knowledge_units
        current_item = current_multi_model_unit

        # As it is list of chunk because of figure & caption unit so, we need to find out only figure unit as reference for placement of current chunk
        unit_of_figure = None
        # Placement details of the current chunk
        #for unit in current_item:
        #    if "table_image_path" in unit:
        page_of_current_unit = current_item.get("page_no.","")
        page_index_of_current_unit = current_item.get("index_on_page","")
        content_of_current_unit = current_item.get("table_image_path","")
        unit_of_figure = current_item
        
        surrounding_pages_units = []


        # Previous page & Next page 
        previous_page = page_of_current_unit - 1
        next_page = page_of_current_unit + 1
        pages_relvant_for_context = [previous_page,page_of_current_unit,next_page]
        # Fetch all the chunks from previous page, current page, and next page (In this hierarchical order)
        for page in pages_relvant_for_context:
            for unit in combined_knowledge_units:
                if unit.get("page_no.") == page:
                    surrounding_pages_units.append(unit)

        # Fetch the index of the current chunk in the list of surrounding chunks
        chunk_window = 2
        index_of_current_unit = surrounding_pages_units.index(unit_of_figure)
        start_index = max(0,index_of_current_unit - chunk_window)
        end_index = min(len(surrounding_pages_units), index_of_current_unit + chunk_window + 1)
        
        # Fetch previous two chunks
        range_of_surrounding_chunks = list(range(start_index, end_index))
        list_of_context_chunks = [surrounding_pages_units[i] for i in range_of_surrounding_chunks if i != index_of_current_unit]


        """
        Imp Note: For multi-model content context extraction, we do not need to store previous & next chunks separately. It is because
        placement of image does not break the continuity of the text chunks, it just enhances the semantic meaning of it. 
        """
        # Fetch the content out of chunks
        context_chunks_text = []
        for lcc in list_of_context_chunks:
            if "raw_content" in lcc:
                context_chunks_text.append(lcc.get("raw_content",""))
            if "table_caption" in lcc:
                context_chunks_text.append(lcc.get("table_caption",""))

        return context_chunks_text











if __name__ == "__main__":

    context_extraction = Context_Extractor()

    multi_model_final_chunks = context_extraction.__run_context_extractor__()

    print(multi_model_final_chunks)

