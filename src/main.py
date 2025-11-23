
from src.document_parsing.data_extraction import MinerU_Parser
from utils import units_splitter

if __name__ == "__main__":

    file_path = knowledge_units_list="C:\\Users\Hp\\Documents\\AI Projects docs\\RAG\\RAG_for_Anything.pdf"
    
    """ Module - 1: Document Parsing  """
    # lets initialize the minerU class
    minerU_testing = MinerU_Parser(data_file_path=file_path)

    combined_knowledge_units = minerU_testing.__run_parser__()

    multi_model_units,textual_units = units_splitter(combined_knowledge_units)

    """ Module - 2: Context Extraction  """

