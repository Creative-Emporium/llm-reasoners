import pickle
from typing import Type, Callable, Optional

import numpy as np
from datasets import load_dataset
from tqdm import tqdm
from datetime import datetime

from reasoners import LanguageModel, Reasoner, SearchAlgorithm
from reasoners.algorithm import DFS

from world_model import crosswordsWorldModel
from search_config import crosswordsConfig
from utils import MiniCrosswordsEnv



def rap_crosswords(base_model: LanguageModel,
              search_algo: Type[SearchAlgorithm] = DFS,
              resume: int = 0,
              n_eval: int = 8,
              depth: int = 5,
              batch_size: int = 2,
              max_per_state: int = 3,
              total_states: int = 100,
              log_dir: Optional[str] = None,
              disable_log: bool = False,
              **search_algo_params):
    
    if not disable_log:
        if log_dir is None:
            log_dir = f'logs/crosswords_{search_algo.__name__}/{datetime.now().strftime("%m%d%Y-%H%M%S")}'
        os.makedirs(log_dir, exist_ok=resume >= 0)
        os.makedirs(os.path.join(log_dir, 'algo_output'), exist_ok=True)
        with open(os.path.join(log_dir, 'args.txt'), 'w') as f:
            print(sys.argv, file=f)

    env = MiniCrosswordsEnv()
    ## keep the best 5 candidates, need at most 4 steps to solve
    ## following ToT, eval step will consider number of times to prompt for state evaluation
    search_algo_params |= {'max_per_state': max_per_state, 'total_states': total_states, 'depth': depth}
    world_model = crosswordsWorldModel(base_model=base_model, batch_size=batch_size)
    config = crosswordsConfig(base_model=base_model,
                         batch_size=batch_size,
                         depth=depth, n_eval=n_eval)
    search_algo = search_algo(**search_algo_params)
    agent = Reasoner(world_model=world_model, search_config=config, search_algo=search_algo)

    correct = 0
    correct_count = 0
    example_cnt = 0
    answer=''
    answer_list = []
    
    for index, i in tqdm(enumerate(range(0, 100, 5))):
        print('\n--------------------------------------------')
        print(f'index: {index}  example: {i}')
        print('--------------------------------------------')
        example_cnt += 1
        algo_output = agent(i, best_state=True)
        best = 0
        output = ''
        ans = ''
        print('********************************************')
        print(f'Output:')
        for output_i, state in enumerate(algo_output):
            print(f'{output_i}  {output}')
            env, actions, info = state
            if best < info['info']['r_word']:
                best = info['info']['r_word']
                output = env.ans
                answer = env.ans_gt
        answer_list.append((output, answer, best, search_algo.stat_cnt))
        if best == 1.0:
            correct = 1
            correct_count += 1
        accuracy = correct_count / example_cnt
        log_str = f'Case #{resume + i}: {correct=}, {output=}, {answer=} ; {accuracy=:.3f} ({correct_count}/{example_cnt})'
        tqdm.write(log_str)
        if not disable_log:
            with open(os.path.join(log_dir, 'result.log'), 'a') as f:
                print(log_str, file=f)
            with open(os.path.join(log_dir, 'algo_output', f'{resume + i + 1}.pkl'), 'wb') as f:
                pickle.dump(algo_output, f)

        break
    for i, result in enumerate(answer_list):
        print('--------------------------------------------')
        print(f'Example {i}  best: {result[2]} stat_cnt: {result[3]}')
        print(f'Pred: {result[0]}')
        print(f'GT  : {result[1]}')
        


if __name__ == '__main__':
    import os
    import sys
    import json
    import warnings
    import fire
    from reasoners.lm import GPTCompletionModel
    import random
    import torch
    import torch.backends.cudnn

    np.random.seed(0)
    random.seed(0)
    torch.manual_seed(0)
    torch.cuda.manual_seed(0)
    torch.backends.cudnn.deterministic = True


    def main(
             batch_size: int = 2,
             prompts: str = 'examples/crosswords/prompts/crosswords.json', # not used
             disable_log: bool = False,
             model: str = 'gpt-3.5-turbo',
             temperature: float = 0.7,
             **kwargs):
        openai_model = GPTCompletionModel(model=model, temperature=temperature)
        #log_dir = 'logs/crosswords_dfs/test-gpt3.5'
        rap_crosswords(base_model=openai_model,
                  batch_size=batch_size, # not used
                  disable_log=disable_log,
                  #log_dir=log_dir,
                  **kwargs)


    fire.Fire(main)
