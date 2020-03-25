#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

import os
import sys
from pprint import pprint

import torch
import torch.nn as nn
import torch.optim
import torch.backends.cudnn as cudnn
from torch.utils.data import DataLoader
from test import test
from train import train

from opt import Options
from src.data_utils_fly import define_actions
import src.log as log

from model import LinearModel, weight_init
from src.data_loader_fun import data_loader


def main(opt):
    start_epoch = 0
    err_best = 1000
    glob_step = 0
    lr_now = opt.lr

    # save options
    log.save_options(opt, opt.ckpt)

    # create model
    model = LinearModel()
    model = model.cuda()
    model.apply(weight_init)
    criterion = nn.MSELoss(size_average=True).cuda()
    optimizer = torch.optim.Adam(model.parameters(), lr=opt.lr)
    
    print(">>> total params: {:.2f}M".format(sum(p.numel() for p in model.parameters()) / 1000000.0))
    
    # load pretrained ckpt
    if opt.load:
        print(">>> loading ckpt from '{}'".format(opt.load))
        ckpt = torch.load(opt.load)
        start_epoch = ckpt['epoch']
        err_best = ckpt['err']
        glob_step = ckpt['step']
        lr_now = ckpt['lr']
        model.load_state_dict(ckpt['state_dict'])
        optimizer.load_state_dict(ckpt['optimizer'])
        print(">>> ckpt loaded (epoch: {} | err: {})".format(start_epoch, err_best))
        
    if opt.resume:
        logger = log.Logger(os.path.join(opt.ckpt, 'log.txt'), resume=True)
    else:
        logger = log.Logger(os.path.join(opt.ckpt, 'log.txt'))
        logger.set_names(['epoch', 'lr', 'loss_train', 'loss_test', 'err_test'])

    # list of action(s)
    actions = define_actions(opt.action)
    pprint(actions, indent=4)

    # data loading
    print("\n>>> loading data")
    
    # load statistics data
    stat_3d = torch.load(os.path.join(opt.data_dir, 'stat_3d.pth.tar'))
    
    # test
    if opt.test:
        for action in actions:
            print (">>> TEST on _{}_".format(action))
            test_loader = DataLoader(
                dataset=data_loader(actions=action, data_path=opt.data_dir, use_hg=opt.use_hg, is_train=False),
                batch_size=opt.test_batch,
                shuffle=False,
                num_workers=opt.job,
                pin_memory=True)
            
            _, err_test = test(test_loader, model, criterion, stat_3d, procrustes=opt.procrustes)
            
            print ("{:.4f}".format(err_test), end='\t')
        sys.exit()

    # load datasets for training
    test_loader = DataLoader(
        dataset=data_loader(actions=actions, data_path=opt.data_dir, use_hg=opt.use_hg, is_train=False),
        batch_size=opt.test_batch,
        shuffle=False,
        num_workers=opt.job,
        pin_memory=True)
    
    train_loader = DataLoader(
        dataset=data_loader(actions=actions, data_path=opt.data_dir, use_hg=opt.use_hg),
        batch_size=opt.train_batch,
        shuffle=True,
        num_workers=opt.job,
        pin_memory=True)
    
    # loop through epochs
    cudnn.benchmark = True
    for epoch in range(start_epoch, opt.epochs):
        print('==========================')
        print('>>> epoch: {} | lr: {:.5f}'.format(epoch + 1, lr_now))

        # train
        glob_step, lr_now, loss_train = train(
            train_loader, model, criterion, optimizer,
            lr_init=opt.lr, lr_now=lr_now, glob_step=glob_step, lr_decay=opt.lr_decay, gamma=opt.lr_gamma,
            max_norm=opt.max_norm)
        
        #test
        loss_test, err_test = test(test_loader, model, criterion, stat_3d, procrustes=opt.procrustes)

        # update log file
        logger.append([epoch + 1, lr_now, loss_train, loss_test, err_test],
                      ['int', 'float', 'float', 'flaot', 'float'])

        # save ckpt
        err_best = min(err_test, err_best)
        log.save_ckpt({'epoch': epoch + 1,
                       'lr': lr_now,
                       'step': glob_step,
                       'err': err_best,
                       'state_dict': model.state_dict(),
                       'optimizer': optimizer.state_dict()},
                        ckpt_path=opt.ckpt,
                        is_best = err_test < err_best)

    logger.close()
    

if __name__ == "__main__":
    option = Options().parse()
    main(option)